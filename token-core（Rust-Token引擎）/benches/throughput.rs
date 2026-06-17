use criterion::{black_box, criterion_group, criterion_main, Criterion};
use token_core::{counter, estimate_tokens, billing::{CostCalculator, pricing}, tokenizer::registry, Message, Role, TokenUsage};

fn bench_count_tokens(c: &mut Criterion) {
    let text = "This is a test sentence for benchmarking token counting performance. ".repeat(100);
    c.bench_function("count_english_100x", |b| {
        b.iter(|| counter::count_tokens(black_box(&text), black_box("claude-sonnet-4-6")))
    });
}

fn bench_count_batch(c: &mut Criterion) {
    let messages: Vec<Message> = (0..1000).map(|i| {
        Message::new(Role::User, format!("Test message number {} with some content.", i), i)
    }).collect();
    c.bench_function("count_batch_1000", |b| {
        b.iter(|| counter::count_batch(black_box(&messages), black_box("claude-sonnet-4-6")))
    });
}

fn bench_estimate(c: &mut Criterion) {
    let text = "hello world ".repeat(1000);
    c.bench_function("estimate_35k_chars", |b| {
        b.iter(|| estimate_tokens(black_box(&text)))
    });
}

fn bench_cost_calculation(c: &mut Criterion) {
    let usage = TokenUsage { prompt_tokens: 100000, completion_tokens: 10000, ..Default::default() };
    let calc = CostCalculator::new();
    c.bench_function("cost_calculate", |b| {
        b.iter(|| calc.calculate(black_box(&usage), black_box("claude-sonnet-4-6"), black_box("online")))
    });
}

criterion_group!(
    benches,
    bench_count_tokens,
    bench_count_batch,
    bench_estimate,
    bench_cost_calculation,
);
criterion_main!(benches);
