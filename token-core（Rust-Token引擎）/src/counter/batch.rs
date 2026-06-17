use crate::counter::count_batch;
use crate::Message;
use rayon::prelude::*;

/// Batch count messages using rayon parallel iteration
/// For large batches (>100 messages), this provides ~N× speedup on multi-core CPUs
pub fn count_batch_parallel(messages: &[Message], model: &str) -> Result<Vec<usize>, crate::TokenError> {
    // For small batches, parallel overhead isn't worth it
    if messages.len() < 100 {
        return count_batch(messages, model);
    }

    let tokenizer = crate::tokenizer::registry::find_tokenizer(model)
        .ok_or_else(|| crate::TokenError::ModelNotFound(model.to_string()))?;

    Ok(messages
        .par_iter()
        .map(|m| tokenizer.count(&m.content))
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Role;

    #[test]
    fn test_parallel_batch() {
        let messages: Vec<Message> = (0..200)
            .map(|i| Message::new(Role::User, format!("Test message number {}", i), i))
            .collect();
        let counts = count_batch_parallel(&messages, "claude-sonnet-4-6").unwrap();
        assert_eq!(counts.len(), 200);
        assert!(counts.iter().all(|&c| c > 0));
    }

    #[test]
    fn test_small_batch_uses_sequential() {
        let messages = vec![Message::new(Role::User, "hello", 0)];
        let counts = count_batch_parallel(&messages, "claude-sonnet-4-6").unwrap();
        assert_eq!(counts.len(), 1);
    }
}
