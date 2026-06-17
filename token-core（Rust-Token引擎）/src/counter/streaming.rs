use crate::counter::estimated;

/// Streaming token counter for SSE/WebSocket scenarios.
/// Maintains a running total and provides incremental updates.

pub struct StreamingCounter {
    total_chars: usize,
    total_tokens: usize,
}

impl StreamingCounter {
    pub fn new() -> Self {
        Self {
            total_chars: 0,
            total_tokens: 0,
        }
    }

    /// Feed a new chunk of text into the counter
    pub fn feed(&mut self, chunk: &str) -> StreamingUpdate {
        let chunk_chars = chunk.len();
        let chunk_tokens = estimated::estimate_tokens_chars(chunk);

        self.total_chars += chunk_chars;
        self.total_tokens += chunk_tokens;

        StreamingUpdate {
            chunk_chars,
            chunk_tokens,
            total_chars: self.total_chars,
            total_tokens: self.total_tokens,
        }
    }

    /// Get current total without feeding new text
    pub fn total(&self) -> (usize, usize) {
        (self.total_chars, self.total_tokens)
    }

    /// Reset the counter for a new stream
    pub fn reset(&mut self) {
        self.total_chars = 0;
        self.total_tokens = 0;
    }
}

impl Default for StreamingCounter {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone)]
pub struct StreamingUpdate {
    pub chunk_chars: usize,
    pub chunk_tokens: usize,
    pub total_chars: usize,
    pub total_tokens: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_streaming_counter() {
        let mut counter = StreamingCounter::new();
        let u1 = counter.feed("Hello, ");
        let u2 = counter.feed("world!");
        assert!(u2.total_tokens > u1.total_tokens);
        assert_eq!(counter.total().0, 13);
    }

    #[test]
    fn test_reset() {
        let mut counter = StreamingCounter::new();
        counter.feed("some text");
        counter.reset();
        assert_eq!(counter.total().0, 0);
    }
}
