use crate::tokenizer::CharTokenizer;
pub fn get_llama_tokenizer() -> CharTokenizer { CharTokenizer::new("llama-default", 3.8) }
