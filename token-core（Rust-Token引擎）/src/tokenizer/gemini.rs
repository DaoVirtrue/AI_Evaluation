use crate::tokenizer::CharTokenizer;
pub fn get_gemini_tokenizer() -> CharTokenizer { CharTokenizer::new("gemini-default", 3.6) }
