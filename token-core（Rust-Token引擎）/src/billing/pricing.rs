use once_cell::sync::Lazy;
use std::collections::HashMap;

/// Thinking mode configuration
#[derive(Debug, Clone)]
pub enum ThinkingMode {
    Adaptive { included_free_tokens: usize },
    Selectable { included_free_tokens: usize },
    None,
}

/// Long context surcharge configuration
#[derive(Debug, Clone)]
pub struct LongContextSurcharge {
    pub threshold: usize,
    pub input_multiplier: f64,
    pub output_multiplier: f64,
}

/// Complete pricing for a single model
#[derive(Debug, Clone)]
pub struct ModelPricing {
    pub id: &'static str,
    pub provider: &'static str,
    pub input_per_million: f64,
    pub output_per_million: f64,
    pub cache_hit_per_million: Option<f64>,
    pub batch_input_per_million: Option<f64>,
    pub batch_output_per_million: Option<f64>,
    pub context_limit: usize,
    pub max_output: usize,
    pub long_context_surcharge: Option<LongContextSurcharge>,
    pub thinking_mode: ThinkingMode,
    pub release_date: &'static str,
    pub swe_bench_score: Option<f64>,
    pub license: Option<&'static str>,
    pub notes: &'static str,
}

/// 2026 Q2 pricing table — all major models as of June 2026
pub static PRICING_2026_Q2: Lazy<Vec<ModelPricing>> = Lazy::new(|| {
    vec![
        // ==================== Anthropic ====================
        ModelPricing {
            id: "claude-fable-5".into(),
            provider: "anthropic",
            input_per_million: 10.00,
            output_per_million: 50.00,
            cache_hit_per_million: None,
            batch_input_per_million: None,
            batch_output_per_million: None,
            context_limit: 1_000_000,
            max_output: 128_000,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::Adaptive { included_free_tokens: 32_000 },
            release_date: "2026-06-09",
            swe_bench_score: Some(95.0),
            license: None,
            notes: "Mythos-class, highest capability",
        },
        ModelPricing {
            id: "claude-opus-4-8".into(),
            provider: "anthropic",
            input_per_million: 5.00,
            output_per_million: 25.00,
            cache_hit_per_million: Some(0.50),
            batch_input_per_million: Some(2.50),
            batch_output_per_million: Some(12.50),
            context_limit: 1_000_000,
            max_output: 128_000,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::Adaptive { included_free_tokens: 32_000 },
            release_date: "2026-05-28",
            swe_bench_score: Some(88.6),
            license: None,
            notes: "Best balance for complex agent tasks",
        },
        ModelPricing {
            id: "claude-sonnet-4-6".into(),
            provider: "anthropic",
            input_per_million: 3.00,
            output_per_million: 15.00,
            cache_hit_per_million: Some(0.30),
            batch_input_per_million: Some(1.50),
            batch_output_per_million: Some(7.50),
            context_limit: 1_000_000,
            max_output: 64_000,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2026-02-17",
            swe_bench_score: Some(79.6),
            license: None,
            notes: "Best speed/intelligence balance",
        },
        ModelPricing {
            id: "claude-haiku-4-5".into(),
            provider: "anthropic",
            input_per_million: 1.00,
            output_per_million: 5.00,
            cache_hit_per_million: Some(0.10),
            batch_input_per_million: Some(0.50),
            batch_output_per_million: Some(2.50),
            context_limit: 200_000,
            max_output: 64_000,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2025-10-01",
            swe_bench_score: Some(73.3),
            license: None,
            notes: "Fastest and cheapest Claude",
        },

        // ==================== OpenAI ====================
        ModelPricing {
            id: "gpt-5.5".into(),
            provider: "openai",
            input_per_million: 5.00,
            output_per_million: 30.00,
            cache_hit_per_million: Some(0.50),
            batch_input_per_million: Some(2.50),
            batch_output_per_million: Some(15.00),
            context_limit: 1_050_000,
            max_output: 128_000,
            long_context_surcharge: Some(LongContextSurcharge {
                threshold: 272_000,
                input_multiplier: 2.0,
                output_multiplier: 1.5,
            }),
            thinking_mode: ThinkingMode::None,
            release_date: "2026-04-23",
            swe_bench_score: Some(88.7),
            license: None,
            notes: ">272K tokens: 2x input surcharge, 1.5x output surcharge",
        },
        ModelPricing {
            id: "gpt-5.4".into(),
            provider: "openai",
            input_per_million: 2.50,
            output_per_million: 15.00,
            cache_hit_per_million: None,
            batch_input_per_million: Some(1.25),
            batch_output_per_million: Some(7.50),
            context_limit: 1_050_000,
            max_output: 128_000,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2026-03-05",
            swe_bench_score: Some(74.0),
            license: None,
            notes: "Good balance for production workloads",
        },
        ModelPricing {
            id: "gpt-4.1".into(),
            provider: "openai",
            input_per_million: 2.00,
            output_per_million: 8.00,
            cache_hit_per_million: Some(0.50),
            batch_input_per_million: Some(1.00),
            batch_output_per_million: Some(4.00),
            context_limit: 1_047_576,
            max_output: 32_768,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2025-04-16",
            swe_bench_score: Some(54.6),
            license: None,
            notes: "Original 1M context model",
        },
        ModelPricing {
            id: "gpt-4.1-mini".into(),
            provider: "openai",
            input_per_million: 0.40,
            output_per_million: 1.60,
            cache_hit_per_million: None,
            batch_input_per_million: Some(0.20),
            batch_output_per_million: Some(0.80),
            context_limit: 1_047_576,
            max_output: 32_768,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2025-04-16",
            swe_bench_score: None,
            license: None,
            notes: "Cheap 1M context for bulk tasks",
        },
        ModelPricing {
            id: "gpt-4.1-nano".into(),
            provider: "openai",
            input_per_million: 0.10,
            output_per_million: 0.40,
            cache_hit_per_million: None,
            batch_input_per_million: None,
            batch_output_per_million: None,
            context_limit: 1_047_576,
            max_output: 16_384,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2025-04-16",
            swe_bench_score: None,
            license: None,
            notes: "Cheapest OpenAI model",
        },

        // ==================== DeepSeek ====================
        ModelPricing {
            id: "deepseek-v4-pro".into(),
            provider: "deepseek",
            input_per_million: 0.435,
            output_per_million: 0.87,
            cache_hit_per_million: Some(0.003625),
            batch_input_per_million: None,
            batch_output_per_million: None,
            context_limit: 1_000_000,
            max_output: 384_000,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::Selectable { included_free_tokens: 0 },
            release_date: "2026-04-24",
            swe_bench_score: Some(80.6),
            license: Some("MIT"),
            notes: "Promotional 75% discount pricing. Standard: $1.74/$3.48",
        },
        ModelPricing {
            id: "deepseek-v4-pro-standard".into(),
            provider: "deepseek",
            input_per_million: 1.74,
            output_per_million: 3.48,
            cache_hit_per_million: Some(0.0145),
            batch_input_per_million: None,
            batch_output_per_million: None,
            context_limit: 1_000_000,
            max_output: 384_000,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::Selectable { included_free_tokens: 0 },
            release_date: "2026-04-24",
            swe_bench_score: Some(80.6),
            license: Some("MIT"),
            notes: "Standard pricing after promo ends",
        },
        ModelPricing {
            id: "deepseek-v4-flash".into(),
            provider: "deepseek",
            input_per_million: 0.14,
            output_per_million: 0.28,
            cache_hit_per_million: Some(0.0028),
            batch_input_per_million: None,
            batch_output_per_million: None,
            context_limit: 1_000_000,
            max_output: 384_000,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2026-04-24",
            swe_bench_score: None,
            license: Some("MIT"),
            notes: "Ultra-cheap 1M context, MIT licensed",
        },

        // ==================== Google Gemini ====================
        ModelPricing {
            id: "gemini-3.1-pro".into(),
            provider: "google",
            input_per_million: 2.00,
            output_per_million: 12.00,
            cache_hit_per_million: Some(0.20),
            batch_input_per_million: None,
            batch_output_per_million: None,
            context_limit: 2_000_000,
            max_output: 64_000,
            long_context_surcharge: Some(LongContextSurcharge {
                threshold: 200_000,
                input_multiplier: 2.0,
                output_multiplier: 1.5,
            }),
            thinking_mode: ThinkingMode::None,
            release_date: "2026-02-19",
            swe_bench_score: Some(77.1),
            license: None,
            notes: "Largest context window (2M). >200K has surcharge",
        },
        ModelPricing {
            id: "gemini-3.5-flash".into(),
            provider: "google",
            input_per_million: 1.50,
            output_per_million: 9.00,
            cache_hit_per_million: None,
            batch_input_per_million: None,
            batch_output_per_million: None,
            context_limit: 1_000_000,
            max_output: 64_000,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2026-05-01",
            swe_bench_score: None,
            license: None,
            notes: "Fast frontier coding agent",
        },
        ModelPricing {
            id: "gemini-3.1-flash-lite".into(),
            provider: "google",
            input_per_million: 0.25,
            output_per_million: 1.50,
            cache_hit_per_million: None,
            batch_input_per_million: None,
            batch_output_per_million: None,
            context_limit: 1_000_000,
            max_output: 64_000,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2026-03-03",
            swe_bench_score: None,
            license: None,
            notes: "Budget Gemini with 1M context",
        },

        // ==================== Open-Source Models ====================
        ModelPricing {
            id: "qwen3-235b-a22b".into(),
            provider: "alibaba",
            input_per_million: 0.10,
            output_per_million: 0.10,
            cache_hit_per_million: None,
            batch_input_per_million: None,
            batch_output_per_million: None,
            context_limit: 131_072,
            max_output: 8_192,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2025-07-01",
            swe_bench_score: None,
            license: Some("Apache-2.0"),
            notes: "Cheapest frontier open model on Fireworks",
        },
        ModelPricing {
            id: "llama-4-maverick".into(),
            provider: "meta",
            input_per_million: 0.20,
            output_per_million: 0.80,
            cache_hit_per_million: None,
            batch_input_per_million: None,
            batch_output_per_million: None,
            context_limit: 1_000_000,
            max_output: 8_192,
            long_context_surcharge: None,
            thinking_mode: ThinkingMode::None,
            release_date: "2025-09-01",
            swe_bench_score: None,
            license: Some("Llama 4 Community"),
            notes: "Open-weight 1M context on DeepInfra",
        },
    ]
});

/// Lazily-built lookup table
pub static PRICING_MAP: Lazy<HashMap<&'static str, &ModelPricing>> = Lazy::new(|| {
    PRICING_2026_Q2
        .iter()
        .map(|p| (p.id, p))
        .collect()
});

/// Get pricing for a model
pub fn get_pricing(model_id: &str) -> Option<&'static ModelPricing> {
    PRICING_MAP.get(model_id).copied()
}

/// Get all models from a provider
pub fn get_models_by_provider(provider: &str) -> Vec<&'static ModelPricing> {
    PRICING_2026_Q2
        .iter()
        .filter(|p| p.provider == provider)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_all_models_have_valid_data() {
        for model in PRICING_2026_Q2.iter() {
            assert!(!model.id.is_empty());
            assert!(model.input_per_million > 0.0);
            assert!(model.output_per_million > 0.0);
            assert!(model.context_limit > 0);
        }
    }

    #[test]
    fn test_get_pricing() {
        let p = get_pricing("claude-sonnet-4-6").unwrap();
        assert_eq!(p.input_per_million, 3.00);
        assert_eq!(p.output_per_million, 15.00);
        assert_eq!(p.context_limit, 1_000_000);
    }

    #[test]
    fn test_unknown_model_returns_none() {
        assert!(get_pricing("nonexistent-model").is_none());
    }

    #[test]
    fn test_long_context_surcharge_models() {
        let gpt55 = get_pricing("gpt-5.5").unwrap();
        let sc = gpt55.long_context_surcharge.as_ref().unwrap();
        assert_eq!(sc.threshold, 272_000);

        let gemini = get_pricing("gemini-3.1-pro").unwrap();
        let sc = gemini.long_context_surcharge.as_ref().unwrap();
        assert_eq!(sc.threshold, 200_000);
    }
}
