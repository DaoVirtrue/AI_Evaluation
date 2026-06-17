pub mod truncation;

use serde::Serialize;

use crate::{Message, TokenError, TruncationResult};
use crate::tokenizer::registry;
use crate::billing::pricing;
use crate::counter::count_total;

/// Check if messages fit within a model's context window
pub fn check_window(messages: &[Message], model: &str) -> Result<WindowStatus, TokenError> {
    let pricing = pricing::get_pricing(model)
        .ok_or_else(|| TokenError::ModelNotFound(model.to_string()))?;
    let total = count_total(messages, model)?;
    let used_pct = (total as f64 / pricing.context_limit as f64) * 100.0;

    Ok(WindowStatus {
        total_tokens: total,
        context_limit: pricing.context_limit,
        remaining: pricing.context_limit.saturating_sub(total),
        used_percentage: used_pct,
        needs_truncation: total > pricing.context_limit,
    })
}

/// Check if messages are within the window, return an error if system prompt alone exceeds limit
pub fn validate_window(messages: &[Message], model: &str) -> Result<WindowStatus, TokenError> {
    let status = check_window(messages, model)?;
    // Check if system prompt alone exceeds limit
    let system_messages: Vec<&Message> = messages.iter().filter(|m| m.role == crate::Role::System).collect();

    if !system_messages.is_empty() {
        let system_tokens: usize = system_messages.iter()
            .map(|m| {
                let t = registry::find_tokenizer(model).unwrap();
                t.count(&m.content)
            })
            .sum();
        if system_tokens > status.context_limit {
            return Err(TokenError::SystemPromptOverflow(system_tokens, status.context_limit));
        }
    }
    Ok(status)
}

/// Truncate messages to fit within the window using the stratified strategy
pub fn truncate(messages: &[Message], model: &str) -> Result<TruncationResult, TokenError> {
    let status = check_window(messages, model)?;
    if !status.needs_truncation {
        return Ok(TruncationResult {
            messages: messages.to_vec(),
            tokens_kept: status.total_tokens,
            tokens_lost: 0,
            truncated_count: 0,
            warning: None,
        });
    }
    truncation::stratified::truncate_stratified(messages, status.context_limit, model)
}

#[derive(Debug, Clone, Serialize)]
pub struct WindowStatus {
    pub total_tokens: usize,
    pub context_limit: usize,
    pub remaining: usize,
    pub used_percentage: f64,
    pub needs_truncation: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Role;

    #[test]
    fn test_check_window() {
        let messages = vec![Message::new(Role::User, "hello", 0)];
        let status = check_window(&messages, "claude-sonnet-4-6").unwrap();
        assert!(!status.needs_truncation);
        assert!(status.total_tokens < status.context_limit);
    }

    #[test]
    fn test_large_input_needs_truncation() {
        let huge = "test ".repeat(300_000); // ~1M chars, well over 1M tokens
        let messages = vec![Message::new(Role::User, &huge, 0)];
        let status = check_window(&messages, "claude-haiku-4-5").unwrap(); // 200K limit
        assert!(status.needs_truncation);
    }

    #[test]
    fn test_invalid_model() {
        let messages = vec![Message::new(Role::User, "hello", 0)];
        assert!(check_window(&messages, "fake").is_err());
    }
}
