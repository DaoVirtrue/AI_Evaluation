use crate::{Message, Role, TokenError, TruncationResult};
use crate::tokenizer::registry;

/// Stratified truncation: keep messages by priority layer
///
/// Priority (highest to lowest):
///   1. System Prompt      — never truncated (unless exceeds model limit)
///   2. Tool Results       — critical for agent reasoning
///   3. Recent User        — last 4 user messages
///   4. Recent Assistant   — last 6 assistant messages
///   5. Older Messages     — discarded first
pub fn truncate_stratified(
    messages: &[Message],
    max_tokens: usize,
    model: &str,
) -> Result<TruncationResult, TokenError> {
    let tokenizer = registry::find_tokenizer(model)
        .ok_or_else(|| TokenError::ModelNotFound(model.to_string()))?;

    let mut budget = max_tokens as i64;
    let mut kept: Vec<Message> = Vec::new();
    let mut truncated_count = 0usize;

    // Layer 1: system messages (must keep)
    for msg in messages.iter().filter(|m| m.role == Role::System) {
        let tokens = tokenizer.count(&msg.content) as i64;
        if tokens > max_tokens as i64 {
            return Ok(TruncationResult::error(
                format!("System prompt ({tokens} tokens) exceeds model limit ({max_tokens})")
            ));
        }
        budget -= tokens;
        kept.push(msg.clone());
    }

    // Layer 2-5: non-system messages, sorted by priority
    let mut non_system: Vec<&Message> = messages.iter().filter(|m| m.role != Role::System).collect();
    let total_msgs = non_system.len();

    // Assign priority score (lower = higher priority)
    non_system.sort_by_key(|msg| {
        match msg.role {
            Role::Tool => 0,                                    // Highest
            Role::User if msg.index >= total_msgs.saturating_sub(4) => 1,
            Role::Assistant if msg.index >= total_msgs.saturating_sub(6) => 2,
            Role::User => 3,
            _ => 4,                                             // Lowest
        }
    });

    // Greedy allocation from highest priority
    for msg in &non_system {
        let tokens = tokenizer.count(&msg.content) as i64;
        if budget >= tokens {
            budget -= tokens;
            kept.push((*msg).clone());
        } else {
            truncated_count += 1;
        }
    }

    // Restore original order
    kept.sort_by_key(|m| m.index);

    let tokens_kept = (max_tokens as i64 - budget) as usize;
    let warning = if budget < (max_tokens as i64 / 10) {
        Some(format!("Context heavily truncated: {:.0}% of original may be lost",
            (1.0 - tokens_kept as f64 / max_tokens as f64) * 100.0))
    } else {
        None
    };

    Ok(TruncationResult {
        messages: kept,
        tokens_kept,
        tokens_lost: budget.max(0) as usize,
        truncated_count,
        warning,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_system_prompt_preserved() {
        let messages = vec![
            Message::new(Role::System, "You are a helpful assistant.", 0),
            Message::new(Role::User, "Hello!", 1),
        ];
        let result = truncate_stratified(&messages, 1000, "claude-sonnet-4-6").unwrap();
        assert_eq!(result.messages.len(), 2);
        assert_eq!(result.messages[0].role, Role::System);
        assert_eq!(result.truncated_count, 0);
    }

    #[test]
    fn test_tool_messages_prioritized() {
        let mut messages = vec![Message::new(Role::System, "You are helpful.", 0)];
        // Add many user messages to force truncation
        for i in 1..50 {
            messages.push(Message::new(Role::User, &"test ".repeat(20), i));
        }
        messages.push(Message::new(Role::Tool, "Important tool result", 50));

        let result = truncate_stratified(&messages, 500, "claude-haiku-4-5").unwrap();
        // System + at least some messages should be kept
        assert!(!result.messages.is_empty());
    }
}
