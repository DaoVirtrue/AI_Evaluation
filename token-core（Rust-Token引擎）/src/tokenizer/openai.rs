use crate::tokenizer::{Tokenizer, CharTokenizer};

pub fn get_openai_tokenizer() -> CharTokenizer {
    CharTokenizer::new("openai-default", 3.7)
}

pub fn get_gpt55_tokenizer() -> CharTokenizer {
    CharTokenizer::new("gpt-5.5", 3.7)
}
