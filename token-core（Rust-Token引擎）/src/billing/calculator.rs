use crate::billing::pricing::{self, ModelPricing, ThinkingMode};
use crate::TokenUsage;
use rust_decimal::Decimal;
use rust_decimal::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostBreakdown {
    pub base_input_cost: f64,
    pub base_output_cost: f64,
    pub cache_savings: f64,
    pub long_context_surcharge: f64,
    pub thinking_cost: f64,
    pub total: f64,
    pub breakdown: CostLineItems,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostLineItems {
    pub input_tokens: usize,
    pub output_tokens: usize,
    pub cache_hit_tokens: usize,
    pub thinking_tokens: usize,
    pub effective_output_tokens: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelCostEstimate {
    pub model: String,
    pub estimated_cost: f64,
    pub capability_score: f64,
    pub cost_per_capability: f64,
}

pub struct CostCalculator;

impl CostCalculator {
    pub fn new() -> Self {
        Self
    }

    /// Calculate cost for a single model call
    pub fn calculate(
        &self,
        usage: &TokenUsage,
        model_id: &str,
        mode: &str, // "online" | "batch"
    ) -> Result<CostBreakdown, crate::TokenError> {
        let pricing = pricing::get_pricing(model_id)
            .ok_or_else(|| crate::TokenError::ModelNotFound(model_id.to_string()))?;

        let is_batch = mode == "batch";

        // Base costs
        let input_price = if is_batch { pricing.batch_input_per_million.unwrap_or(pricing.input_per_million) } else { pricing.input_per_million };
        let output_price = if is_batch { pricing.batch_output_per_million.unwrap_or(pricing.output_per_million) } else { pricing.output_per_million };

        let base_input_cost = Self::tokens_to_dollars(usage.prompt_tokens, input_price);
        let base_output_cost = Self::tokens_to_dollars(usage.completion_tokens, output_price);

        // Cache hit savings
        let cache_savings = pricing.cache_hit_per_million.map(|cache_price| {
            let original = Self::tokens_to_dollars(usage.cache_hit_tokens, pricing.input_per_million);
            let discounted = Self::tokens_to_dollars(usage.cache_hit_tokens, cache_price);
            original - discounted // positive = money saved
        }).unwrap_or(0.0);

        // Long context surcharge
        let long_context_surcharge = pricing.long_context_surcharge.as_ref()
            .filter(|s| usage.prompt_tokens > s.threshold)
            .map(|s| {
                let over = usage.prompt_tokens - s.threshold;
                let extra_input = Self::tokens_to_dollars(over, pricing.input_per_million * (s.input_multiplier - 1.0));
                let extra_output = Self::tokens_to_dollars(usage.completion_tokens, pricing.output_per_million * (s.output_multiplier - 1.0));
                extra_input + extra_output
            }).unwrap_or(0.0);

        // Thinking tokens cost
        let thinking_cost = match &pricing.thinking_mode {
            ThinkingMode::Adaptive { included_free_tokens } |
            ThinkingMode::Selectable { included_free_tokens } => {
                let chargeable = usage.thinking_tokens.saturating_sub(*included_free_tokens);
                Self::tokens_to_dollars(chargeable, pricing.input_per_million)
            }
            ThinkingMode::None => 0.0,
        };

        let total = base_input_cost + base_output_cost - cache_savings + long_context_surcharge + thinking_cost;

        Ok(CostBreakdown {
            base_input_cost,
            base_output_cost,
            cache_savings,
            long_context_surcharge,
            thinking_cost,
            total,
            breakdown: CostLineItems {
                input_tokens: usage.prompt_tokens,
                output_tokens: usage.completion_tokens,
                cache_hit_tokens: usage.cache_hit_tokens,
                thinking_tokens: usage.thinking_tokens,
                effective_output_tokens: usage.effective_output_tokens,
            },
        })
    }

    /// Compare costs across multiple models for the same estimated token usage
    pub fn compare_models(
        &self,
        input_tokens: usize,
        estimated_output: usize,
        candidates: &[&str],
    ) -> Vec<ModelCostEstimate> {
        let mut results: Vec<ModelCostEstimate> = candidates.iter().filter_map(|&model_id| {
            let pricing = pricing::get_pricing(model_id)?;
            let cost = Self::tokens_to_dollars(input_tokens, pricing.input_per_million)
                     + Self::tokens_to_dollars(estimated_output, pricing.output_per_million);
            let capability = pricing.swe_bench_score.unwrap_or(50.0);
            let cost_per_cap = if capability > 0.0 { cost / capability } else { f64::MAX };
            Some(ModelCostEstimate {
                model: model_id.to_string(),
                estimated_cost: cost,
                capability_score: capability,
                cost_per_capability: cost_per_cap,
            })
        }).collect();
        results.sort_by(|a, b| a.estimated_cost.partial_cmp(&b.estimated_cost).unwrap_or(std::cmp::Ordering::Equal));
        results
    }

    fn tokens_to_dollars(tokens: usize, price_per_million: f64) -> f64 {
        (tokens as f64 / 1_000_000.0) * price_per_million
    }
}

impl Default for CostCalculator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_basic() {
        let calc = CostCalculator::new();
        let usage = TokenUsage {
            prompt_tokens: 10_000,
            completion_tokens: 1_000,
            ..Default::default()
        };
        let cost = calc.calculate(&usage, "claude-sonnet-4-6", "online").unwrap();
        assert!(cost.total > 0.0);
        assert_eq!(cost.breakdown.input_tokens, 10_000);
    }

    #[test]
    fn test_calculate_with_cache() {
        let calc = CostCalculator::new();
        let usage = TokenUsage {
            prompt_tokens: 100_000,
            completion_tokens: 10_000,
            cache_hit_tokens: 50_000,
            ..Default::default()
        };
        let cost = calc.calculate(&usage, "claude-sonnet-4-6", "online").unwrap();
        assert!(cost.cache_savings >= 0.0);
    }

    #[test]
    fn test_calculate_long_context_surcharge() {
        let calc = CostCalculator::new();
        let usage = TokenUsage {
            prompt_tokens: 300_000, // Over GPT-5.5 272K threshold
            completion_tokens: 10_000,
            ..Default::default()
        };
        let cost = calc.calculate(&usage, "gpt-5.5", "online").unwrap();
        assert!(cost.long_context_surcharge > 0.0);
    }

    #[test]
    fn test_batch_discount() {
        let calc = CostCalculator::new();
        let usage = TokenUsage {
            prompt_tokens: 10_000,
            completion_tokens: 1_000,
            ..Default::default()
        };
        let online = calc.calculate(&usage, "claude-sonnet-4-6", "online").unwrap();
        let batch = calc.calculate(&usage, "claude-sonnet-4-6", "batch").unwrap();
        assert!(batch.total < online.total);
    }

    #[test]
    fn test_compare_models() {
        let calc = CostCalculator::new();
        let estimates = calc.compare_models(
            100_000,
            20_000,
            &["claude-opus-4-8", "claude-sonnet-4-6", "deepseek-v4-flash"],
        );
        assert_eq!(estimates.len(), 3);
        // DeepSeek V4 Flash should be cheapest
        let cheapest = estimates.iter().min_by(|a, b| a.estimated_cost.partial_cmp(&b.estimated_cost).unwrap()).unwrap();
        assert_eq!(cheapest.model, "deepseek-v4-flash");
    }
}
