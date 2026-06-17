use crate::tokenizer::{Tokenizer, CharTokenizer};
use once_cell::sync::Lazy;
use std::collections::HashMap;

/// Global tokenizer registry
static REGISTRY: Lazy<TokenizerRegistry> = Lazy::new(|| {
    let mut r = TokenizerRegistry::new();
    r.register_defaults();
    r
});

pub struct TokenizerRegistry {
    tokenizers: HashMap<String, Box<dyn Tokenizer>>,
}

impl TokenizerRegistry {
    pub fn new() -> Self {
        Self {
            tokenizers: HashMap::new(),
        }
    }

    fn register_defaults(&mut self) {
        // Claude models: average ~3.5 chars per token
        let claude_models = [
            "claude-fable-5", "claude-opus-4-8", "claude-sonnet-4-6",
            "claude-haiku-4-5", "claude-opus-4-7", "claude-opus-4-6",
        ];
        for m in claude_models {
            self.register(Box::new(CharTokenizer::new(m, 3.5)));
        }

        // OpenAI models: ~3.7 chars per token (tiktoken cl100k_base)
        let openai_models = [
            "gpt-5.5", "gpt-5.4", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
        ];
        for m in openai_models {
            self.register(Box::new(CharTokenizer::new(m, 3.7)));
        }

        // DeepSeek models: ~3.5 chars per token
        let ds_models = ["deepseek-v4-pro", "deepseek-v4-pro-standard", "deepseek-v4-flash"];
        for m in ds_models {
            self.register(Box::new(CharTokenizer::new(m, 3.5)));
        }

        // Gemini models: ~3.6 chars per token
        let gemini_models = [
            "gemini-3.1-pro", "gemini-3.5-flash", "gemini-3.1-flash-lite",
        ];
        for m in gemini_models {
            self.register(Box::new(CharTokenizer::new(m, 3.6)));
        }

        // Qwen models: ~2.8 chars per token (Chinese-optimized)
        self.register(Box::new(CharTokenizer::new("qwen3-235b-a22b", 2.8)));

        // Llama models: ~3.8 chars per token
        self.register(Box::new(CharTokenizer::new("llama-4-maverick", 3.8)));
    }

    pub fn register(&mut self, tokenizer: Box<dyn Tokenizer>) {
        self.tokenizers.insert(tokenizer.model_name().to_string(), tokenizer);
    }

    pub fn get(&self, model: &str) -> Option<&dyn Tokenizer> {
        self.tokenizers.get(model).map(|b| b.as_ref())
    }

    pub fn find(&self, model: &str) -> Option<&dyn Tokenizer> {
        // Exact match first
        if let Some(t) = self.get(model) {
            return Some(t);
        }
        // Fuzzy match: check if model contains a known prefix
        for (key, tok) in &self.tokenizers {
            if model.contains(key.as_str()) || key.contains(model) {
                return Some(tok.as_ref());
            }
        }
        None
    }

    pub fn model_count(&self) -> usize {
        self.tokenizers.len()
    }
}

/// Get the global tokenizer for a model
pub fn get_tokenizer(model: &str) -> Option<&'static dyn Tokenizer> {
    REGISTRY.get(model)
}

/// Get a tokenizer with fuzzy matching
pub fn find_tokenizer(model: &str) -> Option<&'static dyn Tokenizer> {
    REGISTRY.find(model)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_registry_has_models() {
        assert!(REGISTRY.model_count() >= 18);
    }

    #[test]
    fn test_get_claude_tokenizer() {
        let t = get_tokenizer("claude-sonnet-4-6");
        assert!(t.is_some());
        assert!(t.unwrap().count("hello world") > 0);
    }

    #[test]
    fn test_fuzzy_match() {
        let t = find_tokenizer("claude");
        assert!(t.is_some());
    }
}
