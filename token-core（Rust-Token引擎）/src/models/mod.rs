use serde::{Deserialize, Serialize};

/// Multi-dimensional capability scores for each model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelCapability {
    pub model_id: &'static str,
    /// SWE-bench Verified or estimated coding ability (0-100)
    pub coding: f64,
    /// GPQA Diamond or estimated reasoning (0-100)
    pub reasoning: f64,
    /// Needle-in-Haystack recall at 1M tokens (0-100)
    pub long_context_quality: f64,
    /// Estimated tokens per second
    pub speed_tps: f64,
    /// Cost per 1M tokens (blended input+output)
    pub blended_cost: f64,
}

impl ModelCapability {
    /// Composite score weighted by typical agent workload
    pub fn composite(&self) -> f64 {
        self.coding * 0.35 + self.reasoning * 0.30 + self.long_context_quality * 0.20 + (self.speed_tps / 200.0 * 100.0).min(100.0) * 0.15
    }

    /// Cost efficiency: capability per dollar
    pub fn efficiency(&self) -> f64 {
        if self.blended_cost > 0.0 {
            self.composite() / self.blended_cost
        } else {
            f64::MAX
        }
    }
}

pub static CAPABILITIES: &[ModelCapability] = &[
    ModelCapability { model_id: "claude-fable-5", coding: 95.0, reasoning: 95.0, long_context_quality: 95.0, speed_tps: 50.0, blended_cost: 30.0 },
    ModelCapability { model_id: "claude-opus-4-8", coding: 88.6, reasoning: 93.6, long_context_quality: 93.0, speed_tps: 55.0, blended_cost: 15.0 },
    ModelCapability { model_id: "claude-sonnet-4-6", coding: 79.6, reasoning: 88.0, long_context_quality: 90.0, speed_tps: 80.0, blended_cost: 9.0 },
    ModelCapability { model_id: "claude-haiku-4-5", coding: 73.3, reasoning: 82.0, long_context_quality: 70.0, speed_tps: 150.0, blended_cost: 3.0 },
    ModelCapability { model_id: "gpt-5.5", coding: 88.7, reasoning: 93.6, long_context_quality: 88.0, speed_tps: 56.0, blended_cost: 17.5 },
    ModelCapability { model_id: "gpt-5.4", coding: 74.0, reasoning: 92.8, long_context_quality: 50.0, speed_tps: 56.0, blended_cost: 8.75 },
    ModelCapability { model_id: "gpt-4.1", coding: 54.6, reasoning: 78.0, long_context_quality: 85.0, speed_tps: 60.0, blended_cost: 5.0 },
    ModelCapability { model_id: "gpt-4.1-mini", coding: 45.0, reasoning: 65.0, long_context_quality: 80.0, speed_tps: 100.0, blended_cost: 1.0 },
    ModelCapability { model_id: "gpt-4.1-nano", coding: 30.0, reasoning: 40.0, long_context_quality: 75.0, speed_tps: 200.0, blended_cost: 0.25 },
    ModelCapability { model_id: "deepseek-v4-pro", coding: 80.6, reasoning: 88.0, long_context_quality: 90.0, speed_tps: 45.0, blended_cost: 0.65 },
    ModelCapability { model_id: "deepseek-v4-flash", coding: 65.0, reasoning: 75.0, long_context_quality: 85.0, speed_tps: 100.0, blended_cost: 0.21 },
    ModelCapability { model_id: "gemini-3.1-pro", coding: 77.1, reasoning: 94.3, long_context_quality: 85.0, speed_tps: 90.0, blended_cost: 7.0 },
    ModelCapability { model_id: "gemini-3.5-flash", coding: 72.0, reasoning: 85.0, long_context_quality: 80.0, speed_tps: 120.0, blended_cost: 5.25 },
    ModelCapability { model_id: "gemini-3.1-flash-lite", coding: 55.0, reasoning: 70.0, long_context_quality: 75.0, speed_tps: 287.0, blended_cost: 0.875 },
    ModelCapability { model_id: "qwen3-235b-a22b", coding: 60.0, reasoning: 70.0, long_context_quality: 40.0, speed_tps: 120.0, blended_cost: 0.10 },
    ModelCapability { model_id: "llama-4-maverick", coding: 55.0, reasoning: 68.0, long_context_quality: 82.0, speed_tps: 80.0, blended_cost: 0.50 },
];

/// Find capability by model ID (fuzzy match)
pub fn get_capability(model_id: &str) -> Option<&'static ModelCapability> {
    CAPABILITIES.iter().find(|c| c.model_id == model_id)
        .or_else(|| CAPABILITIES.iter().find(|c| model_id.contains(c.model_id) || c.model_id.contains(model_id)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_composite_scores() {
        for c in CAPABILITIES {
            let score = c.composite();
            assert!(score > 0.0 && score <= 100.0, "{} has invalid composite: {}", c.model_id, score);
        }
    }

    #[test]
    fn test_get_capability() {
        assert!(get_capability("claude-opus-4-8").is_some());
        assert!(get_capability("nonexistent").is_none());
    }
}
