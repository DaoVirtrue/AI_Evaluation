pub mod estimated;
pub mod batch;
pub mod streaming;

use crate::tokenizer::registry;
use crate::{Message, TokenError};

/// Count tokens for a single text string using the specified model's tokenizer
pub fn count_tokens(text: &str, model: &str) -> Result<usize, TokenError> {
    let tokenizer = registry::find_tokenizer(model)
        .ok_or_else(|| TokenError::ModelNotFound(model.to_string()))?;
    Ok(tokenizer.count(text))
}

/// Count tokens for a batch of messages
pub fn count_batch(messages: &[Message], model: &str) -> Result<Vec<usize>, TokenError> {
    let tokenizer = registry::find_tokenizer(model)
        .ok_or_else(|| TokenError::ModelNotFound(model.to_string()))?;
    Ok(messages.iter().map(|m| tokenizer.count(&m.content)).collect())
}

/// Count total tokens for all messages
pub fn count_total(messages: &[Message], model: &str) -> Result<usize, TokenError> {
    let counts = count_batch(messages, model)?;
    Ok(counts.iter().sum())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Role;

    #[test]
    fn test_count_tokens_valid_model() {
        let count = count_tokens("Hello, world!", "claude-sonnet-4-6").unwrap();
        assert!(count > 0);
    }

    #[test]
    fn test_count_tokens_invalid_model() {
        let result = count_tokens("Hello", "fake-model");
        assert!(result.is_err());
    }

    #[test]
    fn test_count_batch() {
        let messages = vec![
            Message::new(Role::System, "You are helpful.", 0),
            Message::new(Role::User, "What is AI?", 1),
        ];
        let counts = count_batch(&messages, "claude-sonnet-4-6").unwrap();
        assert_eq!(counts.len(), 2);
        for c in counts {
            assert!(c > 0);
        }
    }
}
