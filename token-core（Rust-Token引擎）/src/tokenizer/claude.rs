use crate::tokenizer::{Tokenizer, CharTokenizer};

pub fn get_claude_tokenizer() -> CharTokenizer {
    CharTokenizer::new("claude-default", 3.5)
}

pub fn get_opus_tokenizer() -> CharTokenizer {
    CharTokenizer::new("claude-opus", 3.5)
}

pub fn get_sonnet_tokenizer() -> CharTokenizer {
    CharTokenizer::new("claude-sonnet", 3.5)
}

pub fn get_haiku_tokenizer() -> CharTokenizer {
    CharTokenizer::new("claude-haiku", 3.5)
}
