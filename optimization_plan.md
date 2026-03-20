# 回填脚本优化计划

## 当前问题分析

### Rate Limit 问题
- BIRB 回填遇到 137+ 次 rate limit
- 当前策略: 每批 50 笔后 sleep 0.5s
- 遇到 429 错误: 等待 2s 重试
- 问题: 固定延迟无法适应 API 负载变化

### 性能瓶颈
1. **批量大小固定**: BATCH_SIZE = 50，不考虑 API 状态
2. **延迟固定**: sleep(0.5)，无论成功或失败
3. **重试策略简单**: 固定等待时间，无指数退避
4. **无动态调整**: 不根据 rate limit 频率调整策略

## 优化方案

### 1. 动态批量大小调整
```python
class AdaptiveBatchSize:
    def __init__(self, initial=50, min_size=10, max_size=100):
        self.size = initial
        self.min_size = min_size
        self.max_size = max_size
        self.success_count = 0
        self.fail_count = 0
    
    def on_success(self):
        self.success_count += 1
        if self.success_count >= 10:  # 连续成功10次
            self.size = min(self.size + 10, self.max_size)
            self.success_count = 0
    
    def on_rate_limit(self):
        self.fail_count += 1
        self.size = max(self.size // 2, self.min_size)  # 减半
        self.success_count = 0
```

### 2. 动态延迟调整
```python
class AdaptiveDelay:
    def __init__(self, initial=0.5, min_delay=0.2, max_delay=5.0):
        self.delay = initial
        self.min_delay = min_delay
        self.max_delay = max_delay
    
    def on_success(self):
        # 成功时逐渐减少延迟
        self.delay = max(self.delay * 0.9, self.min_delay)
    
    def on_rate_limit(self):
        # Rate limit 时增加延迟
        self.delay = min(self.delay * 1.5, self.max_delay)
    
    def wait(self):
        time.sleep(self.delay)
```

### 3. 指数退避重试
```python
def exponential_backoff(attempt, base_delay=2, max_delay=60):
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, 0.1 * delay)  # 添加抖动
    return delay + jitter
```

### 4. Rate Limit 监控
```python
class RateLimitMonitor:
    def __init__(self, window_size=100):
        self.recent_requests = deque(maxlen=window_size)
        self.rate_limit_count = 0
    
    def record_request(self, success):
        self.recent_requests.append(success)
        if not success:
            self.rate_limit_count += 1
    
    def get_success_rate(self):
        if not self.recent_requests:
            return 1.0
        return sum(self.recent_requests) / len(self.recent_requests)
    
    def should_slow_down(self):
        return self.get_success_rate() < 0.8  # 成功率低于80%
```

## 实施计划

### Phase 1: 监控和日志增强（立即）
- 添加详细的 rate limit 统计
- 记录每批的成功率
- 输出当前延迟和批量大小

### Phase 2: 动态调整（BIRB 完成后）
- 实现 AdaptiveBatchSize
- 实现 AdaptiveDelay
- 在 PUMP 回填时测试

### Phase 3: 高级优化（可选）
- 实现指数退避
- 添加 rate limit 预测
- 并行处理多个代币（不同 API key）

## 当前行动

1. **继续 BIRB 回填**（已完成 35%，不中断）
2. **准备优化版本**（用于 PUMP）
3. **更新 CLAUDE.md**（记录优化策略）

## 预期效果

- Rate limit 错误减少 70%
- 整体速度提升 2-3倍
- PUMP 回填时间: 33h → 10-15h
