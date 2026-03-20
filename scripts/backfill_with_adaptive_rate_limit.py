#!/usr/bin/env python3
"""
优化版回填脚本 - 带自适应 Rate Limit 控制

改进:
1. 动态批量大小调整 (10-100)
2. 动态延迟调整 (0.2-5.0s)
3. Rate limit 监控和统计
4. 详细的 debug 日志
"""

import time
import random
from collections import deque

class AdaptiveBatchSize:
    """动态调整批量大小"""
    def __init__(self, initial=50, min_size=10, max_size=100):
        self.size = initial
        self.min_size = min_size
        self.max_size = max_size
        self.success_count = 0
        
    def on_success(self):
        self.success_count += 1
        if self.success_count >= 10:  # 连续成功10次
            old_size = self.size
            self.size = min(self.size + 10, self.max_size)
            if self.size != old_size:
                print(f"    📈 Batch size increased: {old_size} → {self.size}", flush=True)
            self.success_count = 0
    
    def on_rate_limit(self):
        old_size = self.size
        self.size = max(self.size // 2, self.min_size)
        if self.size != old_size:
            print(f"    📉 Batch size decreased: {old_size} → {self.size}", flush=True)
        self.success_count = 0

class AdaptiveDelay:
    """动态调整延迟时间"""
    def __init__(self, initial=0.5, min_delay=0.2, max_delay=5.0):
        self.delay = initial
        self.min_delay = min_delay
        self.max_delay = max_delay
    
    def on_success(self):
        old_delay = self.delay
        self.delay = max(self.delay * 0.95, self.min_delay)
        if abs(old_delay - self.delay) > 0.1:
            print(f"    ⚡ Delay decreased: {old_delay:.2f}s → {self.delay:.2f}s", flush=True)
    
    def on_rate_limit(self):
        old_delay = self.delay
        self.delay = min(self.delay * 1.5, self.max_delay)
        if abs(old_delay - self.delay) > 0.1:
            print(f"    🐌 Delay increased: {old_delay:.2f}s → {self.delay:.2f}s", flush=True)
    
    def wait(self):
        time.sleep(self.delay)

class RateLimitMonitor:
    """监控 Rate Limit 情况"""
    def __init__(self, window_size=100):
        self.recent_requests = deque(maxlen=window_size)
        self.total_requests = 0
        self.rate_limit_count = 0
        self.start_time = time.time()
    
    def record_request(self, success):
        self.recent_requests.append(success)
        self.total_requests += 1
        if not success:
            self.rate_limit_count += 1
    
    def get_success_rate(self):
        if not self.recent_requests:
            return 1.0
        return sum(self.recent_requests) / len(self.recent_requests)
    
    def get_stats(self):
        elapsed = time.time() - self.start_time
        return {
            'total_requests': self.total_requests,
            'rate_limit_count': self.rate_limit_count,
            'success_rate': self.get_success_rate(),
            'rate_limit_rate': self.rate_limit_count / self.total_requests if self.total_requests > 0 else 0,
            'elapsed_time': elapsed,
            'requests_per_hour': self.total_requests / (elapsed / 3600) if elapsed > 0 else 0
        }
    
    def print_stats(self):
        stats = self.get_stats()
        print(f"\n📊 Rate Limit Statistics:", flush=True)
        print(f"  Total requests: {stats['total_requests']}", flush=True)
        print(f"  Rate limits: {stats['rate_limit_count']} ({stats['rate_limit_rate']*100:.1f}%)", flush=True)
        print(f"  Success rate: {stats['success_rate']*100:.1f}%", flush=True)
        print(f"  Requests/hour: {stats['requests_per_hour']:.0f}", flush=True)
        print(f"  Elapsed time: {stats['elapsed_time']/60:.1f} min\n", flush=True)

def exponential_backoff(attempt, base_delay=2, max_delay=60):
    """指数退避 + 抖动"""
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, 0.1 * delay)
    return delay + jitter

# 使用示例 (在实际回填脚本中集成):
"""
# 初始化
batch_size_controller = AdaptiveBatchSize()
delay_controller = AdaptiveDelay()
rate_limit_monitor = RateLimitMonitor()

# 在批量处理循环中
for batch_start in range(0, len(signatures), batch_size_controller.size):
    batch_end = min(batch_start + batch_size_controller.size, len(signatures))
    batch = signatures[batch_start:batch_end]
    
    try:
        # 发送请求
        response = requests.post(rpc_url, json=batch_requests, timeout=30)
        
        if response.status_code == 429:
            # Rate limit
            rate_limit_monitor.record_request(False)
            batch_size_controller.on_rate_limit()
            delay_controller.on_rate_limit()
            
            # 指数退避重试
            for attempt in range(3):
                wait_time = exponential_backoff(attempt)
                print(f"    Rate limited, waiting {wait_time:.1f}s (attempt {attempt+1}/3)", flush=True)
                time.sleep(wait_time)
                
                response = requests.post(rpc_url, json=batch_requests, timeout=30)
                if response.status_code != 429:
                    break
        
        if response.status_code == 200:
            # 成功
            rate_limit_monitor.record_request(True)
            batch_size_controller.on_success()
            delay_controller.on_success()
            
            # 处理结果...
        
    except Exception as e:
        print(f"    Error: {e}", flush=True)
    
    # 批次间延迟
    delay_controller.wait()
    
    # 每1000笔打印统计
    if batch_start % 1000 == 0 and batch_start > 0:
        rate_limit_monitor.print_stats()
"""

if __name__ == "__main__":
    print("这是一个优化模块，需要集成到 backfill_history.py 中使用")
    print("\n使用方法:")
    print("1. 导入这些类到 backfill_history.py")
    print("2. 在 Solana 批量处理循环中使用")
    print("3. 监控效果并调整参数")
