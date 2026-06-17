use crate::tokenizer::CharTokenizer;
pub fn get_deepseek_tokenizer() -> CharTokenizer { CharTokenizer::new("deepseek-default", 3.5) }
