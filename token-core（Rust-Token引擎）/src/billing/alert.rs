use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BudgetAlert {
    pub exceeded: bool,
    pub current_spend: f64,
    pub budget_limit: f64,
    pub usage_pct: f64,
    pub message: String,
}

pub struct BudgetAlerter {
    daily_budget: Option<f64>,
    weekly_budget: Option<f64>,
    monthly_budget: Option<f64>,
    daily_spend: f64,
    weekly_spend: f64,
    monthly_spend: f64,
}

impl BudgetAlerter {
    pub fn new(daily: Option<f64>, weekly: Option<f64>, monthly: Option<f64>) -> Self {
        Self {
            daily_budget: daily,
            weekly_budget: weekly,
            monthly_budget: monthly,
            daily_spend: 0.0,
            weekly_spend: 0.0,
            monthly_spend: 0.0,
        }
    }

    /// Record a new spend
    pub fn record(&mut self, cost: f64) -> Vec<BudgetAlert> {
        self.daily_spend += cost;
        self.weekly_spend += cost;
        self.monthly_spend += cost;
        self.check_alerts()
    }

    /// Check all budget thresholds
    pub fn check_alerts(&self) -> Vec<BudgetAlert> {
        let mut alerts = Vec::new();

        if let Some(limit) = self.daily_budget {
            alerts.push(self.build_alert(self.daily_spend, limit, "daily"));
        }
        if let Some(limit) = self.weekly_budget {
            alerts.push(self.build_alert(self.weekly_spend, limit, "weekly"));
        }
        if let Some(limit) = self.monthly_budget {
            alerts.push(self.build_alert(self.monthly_spend, limit, "monthly"));
        }

        alerts.retain(|a| a.exceeded);
        alerts
    }

    fn build_alert(&self, spend: f64, limit: f64, period: &str) -> BudgetAlert {
        let pct = (spend / limit * 100.0).min(999.9);
        BudgetAlert {
            exceeded: spend > limit,
            current_spend: spend,
            budget_limit: limit,
            usage_pct: pct,
            message: if spend > limit {
                format!("{period} budget exceeded: ${spend:.2} > ${limit:.2} ({pct:.0}%)")
            } else {
                format!("{period} budget: ${spend:.2} / ${limit:.2} ({pct:.0}%)")
            },
        }
    }

    /// Detect anomalous spending (single call > 10x average)
    pub fn detect_anomaly(&self, cost: f64, avg_cost: f64) -> Option<String> {
        if avg_cost > 0.0 && cost > avg_cost * 10.0 {
            let ratio = cost / avg_cost;
            Some(format!(
                "Anomalous spend detected: ${cost:.4} is {ratio:.0}x the average (${avg_cost:.4})"
            ))
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_budget_alert() {
        let mut alerter = BudgetAlerter::new(Some(5.0), None, None);
        let alerts = alerter.record(6.0);
        assert_eq!(alerts.len(), 1);
        assert!(alerts[0].exceeded);
    }

    #[test]
    fn test_no_alert() {
        let mut alerter = BudgetAlerter::new(Some(5.0), None, None);
        let alerts = alerter.record(1.0);
        assert_eq!(alerts.len(), 0);
    }

    #[test]
    fn test_anomaly_detection() {
        let alerter = BudgetAlerter::new(None, None, None);
        let msg = alerter.detect_anomaly(10.0, 0.5);
        assert!(msg.is_some());
    }
}
