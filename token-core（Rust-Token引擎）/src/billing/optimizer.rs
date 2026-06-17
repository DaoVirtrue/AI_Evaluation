use crate::billing::pricing::{self, ModelPricing};
use serde::{Deserialize, Serialize};

/// Task complexity classification
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum TaskComplexity {
    Simple,     // Classification, extraction, summarization
    Moderate,   // Medium reasoning, basic coding
    Complex,    // Multi-step agent tasks
    Extreme,    // Hardest reasoning, frontier math
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizationSuggestion {
    pub title: String,
    pub description: String,
    pub estimated_saving_pct: f64,
    pub priority: Priority,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Priority {
    High,
    Medium,
    Low,
}

pub struct CostOptimizer;

impl CostOptimizer {
    pub fn new() -> Self { Self }

    /// Suggest cheaper models for simple tasks
    pub fn suggest_for_complexity(&self, complexity: &TaskComplexity, current_model: &str) -> Vec<OptimizationSuggestion> {
        let current = match pricing::get_pricing(current_model) {
            Some(p) => p,
            None => return vec![],
        };

        match complexity {
            TaskComplexity::Simple => {
                if current.input_per_million > 1.50 {
                    vec![OptimizationSuggestion {
                        title: "Switch to cheaper model for simple tasks".into(),
                        description: format!(
                            "{} costs ${:.2}/M input. For simple tasks, consider haiku-4-5 ($1.00/M) or deepseek-v4-flash ($0.14/M) with ~80% cost reduction.",
                            current_model, current.input_per_million
                        ),
                        estimated_saving_pct: 80.0,
                        priority: Priority::High,
                    }]
                } else {
                    vec![]
                }
            }
            TaskComplexity::Moderate => {
                if current.input_per_million > 3.00 {
                    vec![OptimizationSuggestion {
                        title: "Consider mid-tier models".into(),
                        description: "For moderate tasks, deepseek-v4-pro ($0.435/M) or sonnet-4-6 ($3.00/M) offer good capability/cost balance.".into(),
                        estimated_saving_pct: 70.0,
                        priority: Priority::Medium,
                    }]
                } else {
                    vec![]
                }
            }
            _ => vec![],
        }
    }

    /// Suggest enabling prompt caching
    pub fn suggest_caching(&self, current_model: &str, cache_hit_pct: f64) -> Vec<OptimizationSuggestion> {
        let pricing = match pricing::get_pricing(current_model) {
            Some(p) => p,
            None => return vec![],
        };

        if cache_hit_pct < 10.0 && pricing.cache_hit_per_million.is_some() {
            vec![OptimizationSuggestion {
                title: "Enable Prompt Caching".into(),
                description: format!(
                    "Cache hit rate is only {:.0}%. Enabling prompt caching on {} can save up to 90% on repeated input tokens.",
                    cache_hit_pct, current_model
                ),
                estimated_saving_pct: 50.0,
                priority: Priority::High,
            }]
        } else {
            vec![]
        }
    }

    /// Suggest for long-context scenarios
    pub fn suggest_long_context(&self, current_model: &str, prompt_tokens: usize) -> Vec<OptimizationSuggestion> {
        let pricing = match pricing::get_pricing(current_model) {
            Some(p) => p,
            None => return vec![],
        };

        if let Some(ref surcharge) = pricing.long_context_surcharge {
            if prompt_tokens > surcharge.threshold {
                vec![OptimizationSuggestion {
                    title: "Long context surcharge detected".into(),
                    description: format!(
                        "{} charges {:.0}x for prompts >{}K tokens. Consider switching to deepseek-v4-pro or claude models (no surcharge for 1M context).",
                        current_model, surcharge.input_multiplier, surcharge.threshold / 1000
                    ),
                    estimated_saving_pct: 50.0,
                    priority: Priority::High,
                }]
            } else {
                vec![]
            }
        } else {
            vec![]
        }
    }
}

impl Default for CostOptimizer {
    fn default() -> Self { Self::new() }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simple_task_suggestion() {
        let opt = CostOptimizer::new();
        let suggestions = opt.suggest_for_complexity(&TaskComplexity::Simple, "claude-opus-4-8");
        assert!(!suggestions.is_empty());
        assert_eq!(suggestions[0].priority, Priority::High);
    }

    #[test]
    fn test_caching_suggestion() {
        let opt = CostOptimizer::new();
        let suggestions = opt.suggest_caching("claude-sonnet-4-6", 3.0);
        assert!(!suggestions.is_empty());
    }

    #[test]
    fn test_long_context_gpt55() {
        let opt = CostOptimizer::new();
        let suggestions = opt.suggest_long_context("gpt-5.5", 300_000);
        assert!(!suggestions.is_empty());
    }
}
