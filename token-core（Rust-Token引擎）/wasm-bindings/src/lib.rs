use wasm_bindgen::prelude::*;
use token_core as tc;

#[wasm_bindgen]
pub fn count_tokens(text: &str, model: &str) -> Result<usize, JsValue> {
    tc::check_input_size(text)
        .map_err(|e| JsValue::from_str(&e.to_string()))?;
    tc::counter::count_tokens(text, model)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

#[wasm_bindgen]
pub fn estimate_tokens(text: &str) -> usize {
    tc::estimate_tokens(text)
}

#[wasm_bindgen]
pub fn calculate_cost(
    prompt_tokens: usize,
    completion_tokens: usize,
    cache_hit_tokens: usize,
    model: &str,
) -> Result<String, JsValue> {
    let usage = tc::TokenUsage {
        prompt_tokens,
        completion_tokens,
        cache_hit_tokens,
        ..Default::default()
    };
    let calc = tc::billing::CostCalculator::new();
    let cost = calc.calculate(&usage, model, "online")
        .map_err(|e| JsValue::from_str(&e.to_string()))?;
    serde_json::to_string(&cost)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

#[wasm_bindgen]
pub fn list_models_json() -> String {
    serde_json::to_string(&tc::list_models()).unwrap_or_default()
}

#[wasm_bindgen]
pub fn compare_models_json(
    input_tokens: usize,
    estimated_output: usize,
    candidates_json: &str,
) -> String {
    let candidates: Vec<&str> = serde_json::from_str(candidates_json).unwrap_or_default();
    let calc = tc::billing::CostCalculator::new();
    let results = calc.compare_models(input_tokens, estimated_output, &candidates);
    serde_json::to_string(&results).unwrap_or_default()
}
