use crate::tokenizer::CharTokenizer;
pub fn get_qwen_tokenizer() -> CharTokenizer { CharTokenizer::new("qwen-default", 2.8) }
