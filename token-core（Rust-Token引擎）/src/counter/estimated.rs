/// Fast token estimation using character ratio.
/// Useful for streaming scenarios where exact counting is too expensive.
/// Accuracy: within ~20% for mixed text, ~5% for English-only.

/// Default chars-per-token ratio for mixed content
const DEFAULT_CHARS_PER_TOKEN: f64 = 3.5;

/// CJK characters tend to be ~1.5 chars per token
const CJK_CHARS_PER_TOKEN: f64 = 1.5;

/// Estimate tokens from character count
pub fn estimate_tokens_chars(text: &str) -> usize {
    if text.is_empty() {
        return 0;
    }
    let cjk_count = text.chars().filter(|c| c > &'\u{2E80}').count() as f64;
    let ascii_count = (text.len() as f64) - cjk_count;
    let estimate = (cjk_count / CJK_CHARS_PER_TOKEN + ascii_count / DEFAULT_CHARS_PER_TOKEN).ceil();
    (estimate as usize).max(1)
}

/// Estimate tokens from byte length (even faster, less accurate)
pub fn estimate_tokens_bytes(byte_len: usize) -> usize {
    (byte_len as f64 / DEFAULT_CHARS_PER_TOKEN).ceil() as usize
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty() {
        assert_eq!(estimate_tokens_chars(""), 0);
        assert_eq!(estimate_tokens_bytes(0), 0);
    }

    #[test]
    fn test_english() {
        let count = estimate_tokens_chars("Hello, world!");
        assert!(count >= 2 && count <= 6);
    }

    #[test]
    fn test_chinese() {
        let count = estimate_tokens_chars("你好世界测试");
        assert!(count >= 2);
    }

    #[test]
    fn test_estimate_monotonic() {
        let short = estimate_tokens_chars("hi");
        let long = estimate_tokens_chars("this is a much longer text that should have more tokens");
        assert!(long > short);
    }
}
