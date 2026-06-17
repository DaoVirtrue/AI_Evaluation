#![forbid(unsafe_code)]

pub mod billing;
pub mod context;
pub mod counter;
pub mod models;
pub mod tokenizer;

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Core error type for token-core
#[derive(Error, Debug)]
pub enum TokenError {
    #[error("Model '{0}' not found in registry")]
    ModelNotFound(String),

    #[error("Input exceeds maximum allowed size: {0} characters (max: {1})")]
    InputTooLarge(usize, usize),

    #[error("System prompt exceeds model context limit: {0} tokens > {1}")]
    SystemPromptOverflow(usize, usize),

    #[error("Tokenizer error: {0}")]
    TokenizerError(String),

    #[error("Invalid parameter: {0}")]
    InvalidParameter(String),
}

pub const MAX_INPUT_CHARS: usize = 10_000_000;

/// Message role in a conversation
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    System,
    User,
    Assistant,
    Tool,
}

/// A single message in a conversation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: Role,
    pub content: String,
    #[serde(default)]
    pub index: usize,
}

impl Message {
    pub fn new(role: Role, content: impl Into<String>, index: usize) -> Self {
        Self {
            role,
            content: content.into(),
            index,
        }
    }

    pub fn is_recent(&self, n: usize) -> bool {
        self.index >= n
    }
}

/// Token usage statistics
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TokenUsage {
    #[serde(default)]
    pub prompt_tokens: usize,
    #[serde(default)]
    pub completion_tokens: usize,
    #[serde(default)]
    pub cache_hit_tokens: usize,
    #[serde(default)]
    pub thinking_tokens: usize,
    #[serde(default)]
    pub effective_output_tokens: usize,
}

/// Cost calculation options
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostOptions {
    #[serde(default = "default_mode")]
    pub mode: String, // "online" | "batch"
    #[serde(default)]
    pub inference_geo: Option<String>,
}

fn default_mode() -> String {
    "online".to_string()
}

impl Default for CostOptions {
    fn default() -> Self {
        Self {
            mode: "online".to_string(),
            inference_geo: None,
        }
    }
}

/// Result of context window truncation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TruncationResult {
    pub messages: Vec<Message>,
    pub tokens_kept: usize,
    pub tokens_lost: usize,
    pub truncated_count: usize,
    pub warning: Option<String>,
}

impl TruncationResult {
    pub fn error(msg: impl Into<String>) -> Self {
        Self {
            messages: vec![],
            tokens_kept: 0,
            tokens_lost: 0,
            truncated_count: 0,
            warning: Some(msg.into()),
        }
    }
}

/// Check input size before processing
pub fn check_input_size(text: &str) -> Result<(), TokenError> {
    if text.len() > MAX_INPUT_CHARS {
        Err(TokenError::InputTooLarge(text.len(), MAX_INPUT_CHARS))
    } else {
        Ok(())
    }
}

/// Get all registered model IDs
pub fn list_models() -> Vec<String> {
    billing::pricing::PRICING_2026_Q2
        .iter()
        .map(|p| p.id.to_string())
        .collect()
}

/// Estimate tokens quickly using character ratio
pub fn estimate_tokens(text: &str) -> usize {
    counter::estimated::estimate_tokens_chars(text)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_estimate_tokens() {
        let english = "Hello, world!";
        let count = estimate_tokens(english);
        assert!(count > 0 && count <= english.len());

        let chinese = "你好世界";
        let count = estimate_tokens(chinese);
        assert!(count > 0);
    }

    #[test]
    fn test_check_input_size() {
        assert!(check_input_size("hello").is_ok());
        let huge = "x".repeat(MAX_INPUT_CHARS + 1);
        assert!(check_input_size(&huge).is_err());
    }
}
