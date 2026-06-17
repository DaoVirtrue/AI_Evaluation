pub mod claude;
pub mod deepseek;
pub mod gemini;
pub mod llama;
pub mod openai;
pub mod qwen;
pub mod registry;

pub use registry::TokenizerRegistry;

/// Trait that all tokenizers must implement
pub trait Tokenizer: Send + Sync {
    fn encode(&self, text: &str) -> Vec<usize>;
    fn decode(&self, tokens: &[usize]) -> String;
    fn count(&self, text: &str) -> usize {
        self.encode(text).len()
    }
    fn model_name(&self) -> &str;
}

/// Simple BPE-like tokenizer using character-based estimation as fallback
/// In production, this would use tiktoken-rs / HuggingFace tokenizers
/// For now, we provide accurate estimation with the architecture to plug in real tokenizers

pub struct CharTokenizer {
    model: String,
    chars_per_token: f64,
}

impl CharTokenizer {
    pub fn new(model: impl Into<String>, chars_per_token: f64) -> Self {
        Self {
            model: model.into(),
            chars_per_token,
        }
    }
}

impl Tokenizer for CharTokenizer {
    fn encode(&self, text: &str) -> Vec<usize> {
        // Simplified: split by whitespace and punctuation
        // Real implementation would use tiktoken or HuggingFace
        text.split(|c: char| c.is_whitespace() || c.is_ascii_punctuation())
            .filter(|s| !s.is_empty())
            .map(|s| s.len())
            .collect()
    }

    fn decode(&self, tokens: &[usize]) -> String {
        tokens.iter().map(|&t| format!("[token_{}]", t)).collect()
    }

    fn count(&self, text: &str) -> usize {
        // Accurate estimation using the model-specific ratio
        let byte_count = text.len() as f64;
        // CJK characters = roughly 1 char per token
        let cjk_chars = text.chars().filter(|c| c > &'\u{2E80}').count() as f64;
        let ascii_chars = byte_count - cjk_chars;
        let estimate = (cjk_chars / 1.5 + ascii_chars / self.chars_per_token).ceil();
        (estimate as usize).max(1)
    }

    fn model_name(&self) -> &str {
        &self.model
    }
}

/// A simple test to verify tokenizer behavior
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_char_tokenizer_english() {
        let t = CharTokenizer::new("test", 4.0);
        let count = t.count("Hello, world! This is a test.");
        assert!(count > 0);
        assert!(count < 50);
    }

    #[test]
    fn test_char_tokenizer_chinese() {
        let t = CharTokenizer::new("test", 4.0);
        let count = t.count("你好世界，这是一个测试");
        assert!(count > 0);
    }

    #[test]
    fn test_char_tokenizer_empty() {
        let t = CharTokenizer::new("test", 4.0);
        assert_eq!(t.count(""), 0);
    }
}
