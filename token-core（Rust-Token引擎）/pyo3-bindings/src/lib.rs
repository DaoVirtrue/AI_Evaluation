use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use token_core as tc;

macro_rules! tc_try {
    ($expr:expr) => {
        $expr.map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
    };
}

/// Python wrapper for token-core
#[pymodule]
fn token_core_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(count_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(count_batch, m)?)?;
    m.add_function(wrap_pyfunction!(estimate_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_cost, m)?)?;
    m.add_function(wrap_pyfunction!(compare_models, m)?)?;
    m.add_function(wrap_pyfunction!(truncate_messages, m)?)?;
    m.add_function(wrap_pyfunction!(check_window, m)?)?;
    m.add_function(wrap_pyfunction!(list_models, m)?)?;
    m.add_function(wrap_pyfunction!(get_pricing_info, m)?)?;
    Ok(())
}

#[derive(Deserialize)]
struct MessageInput {
    role: String,
    content: String,
    #[serde(default)]
    index: usize,
}

#[derive(Deserialize)]
struct UsageInput {
    prompt_tokens: usize,
    completion_tokens: usize,
    #[serde(default)]
    cache_hit_tokens: usize,
    #[serde(default)]
    thinking_tokens: usize,
    #[serde(default)]
    effective_output_tokens: usize,
}

#[derive(Serialize)]
struct CostOutput {
    base_input_cost: f64,
    base_output_cost: f64,
    cache_savings: f64,
    long_context_surcharge: f64,
    thinking_cost: f64,
    total: f64,
    breakdown: serde_json::Value,
}

#[derive(Serialize)]
struct TruncationOutput {
    messages: Vec<serde_json::Value>,
    tokens_kept: usize,
    tokens_lost: usize,
    truncated_count: usize,
    warning: Option<String>,
}

/// Count tokens for a single text
#[pyfunction]
fn count_tokens(text: &str, model: &str) -> PyResult<usize> {
    tc_try!(tc::check_input_size(text));
    Ok(tc_try!(tc::counter::count_tokens(text, model)))
}

/// Count tokens for a batch of messages
#[pyfunction]
fn count_batch(messages_json: &str, model: &str) -> PyResult<Vec<usize>> {
    let messages: Vec<MessageInput> = serde_json::from_str(messages_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    let tc_messages: Vec<tc::Message> = messages.iter().enumerate().map(|(i, m)| {
        let role = match m.role.as_str() {
            "system" => tc::Role::System,
            "user" => tc::Role::User,
            "assistant" => tc::Role::Assistant,
            "tool" => tc::Role::Tool,
            _ => tc::Role::User,
        };
        tc::Message::new(role, &m.content, m.index.max(i))
    }).collect();
    tc::counter::count_batch(&tc_messages, model)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
}

/// Quick token estimation
#[pyfunction]
fn estimate_tokens(text: &str) -> usize {
    tc::estimate_tokens(text)
}

/// Calculate cost for token usage
#[pyfunction]
fn calculate_cost(usage_json: &str, model: &str, mode: &str) -> PyResult<String> {
    let usage: UsageInput = serde_json::from_str(usage_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    let tc_usage = tc::TokenUsage {
        prompt_tokens: usage.prompt_tokens,
        completion_tokens: usage.completion_tokens,
        cache_hit_tokens: usage.cache_hit_tokens,
        thinking_tokens: usage.thinking_tokens,
        effective_output_tokens: usage.effective_output_tokens,
    };
    let calc = tc::billing::CostCalculator::new();
    let cost = calc.calculate(&tc_usage, model, mode)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    serde_json::to_string(&cost)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
}

/// Compare models for a given token estimate
#[pyfunction]
fn compare_models(input_tokens: usize, estimated_output: usize, candidates_json: &str) -> PyResult<String> {
    let candidates: Vec<String> = serde_json::from_str(candidates_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    let candidate_refs: Vec<&str> = candidates.iter().map(|s| s.as_str()).collect();
    let calc = tc::billing::CostCalculator::new();
    let results = calc.compare_models(input_tokens, estimated_output, &candidate_refs);
    serde_json::to_string(&results)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
}

/// Truncate messages to fit context window
#[pyfunction]
fn truncate_messages(messages_json: &str, model: &str) -> PyResult<String> {
    let messages: Vec<MessageInput> = serde_json::from_str(messages_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    let tc_messages: Vec<tc::Message> = messages.iter().enumerate().map(|(i, m)| {
        let role = match m.role.as_str() {
            "system" => tc::Role::System,
            "user" => tc::Role::User,
            "assistant" => tc::Role::Assistant,
            "tool" => tc::Role::Tool,
            _ => tc::Role::User,
        };
        tc::Message::new(role, &m.content, m.index.max(i))
    }).collect();
    let result = tc::context::truncate(&tc_messages, model)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    serde_json::to_string(&result)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
}

/// Check context window status
#[pyfunction]
fn check_window(messages_json: &str, model: &str) -> PyResult<String> {
    let messages: Vec<MessageInput> = serde_json::from_str(messages_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    let tc_messages: Vec<tc::Message> = messages.iter().enumerate().map(|(i, m)| {
        let role = match m.role.as_str() {
            "system" => tc::Role::System,
            "user" => tc::Role::User,
            "assistant" => tc::Role::Assistant,
            "tool" => tc::Role::Tool,
            _ => tc::Role::User,
        };
        tc::Message::new(role, &m.content, m.index.max(i))
    }).collect();
    let result = tc::context::check_window(&tc_messages, model)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    serde_json::to_string(&result)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
}

/// List all registered models
#[pyfunction]
fn list_models() -> Vec<String> {
    tc::list_models()
}

/// Get pricing info for a model
#[pyfunction]
fn get_pricing_info(model: &str) -> PyResult<String> {
    let pricing = tc::billing::pricing::get_pricing(model)
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Model not found"))?;
    let info = serde_json::json!({
        "id": pricing.id,
        "provider": pricing.provider,
        "input_per_million": pricing.input_per_million,
        "output_per_million": pricing.output_per_million,
        "context_limit": pricing.context_limit,
        "max_output": pricing.max_output,
        "release_date": pricing.release_date,
        "notes": pricing.notes,
    });
    serde_json::to_string(&info)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
}
