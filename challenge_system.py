# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("QUANTITATIVE STRATEGY OPTIMIZATION CHALLENGE v1.0")
print("=" * 70)
print()
print("TARGETS:")
print("  10% rate > 60% | 30% rate > 40% | Win rate > 75%")
print()

print("--- PHASES ---")
print("""
[P1] Factor Discovery (1-2 days)
  Goal: Find valid factors
  Methods: Single factor test, simple combos
  
[P2] Combo Optimization (2-3 days)
  Goal: Find optimal combination  
  Methods: Grid search, stepwise factor addition
  
[P3] Fine Tuning (3-5 days)
  Goal: Parameter optimization + overfitting detection
  Methods: Threshold scanning, walk-forward analysis
  
[P4] Live Verification (ongoing)
  Goal: Track and optimize
  Methods: Daily monitoring, weekly review
""")

print("--- VERIFIED FACTORS ---")
print("""
consec>=4      : base 21.9% 10% rate
+ shrink      : +27.0% 10% rate  
+ range_shrink : +10.0% 10% rate
+ uniform      : +5.0% 10% rate
rsi filter     : +5.0% 10% rate
""")

print("--- BEST STRATEGIES ---")
print("""
[V96] consec>=4 + shrink + range_shrink
      80d hold | 10%=65.1% | 30%=33.3% | win=71.4% | n=63
      Limitation: Very rare signals
      
[V94] consec>=4 + shrink + uniform + range_shrink
      60d hold | 10%=59.3% | 30%=22.0% | win=69.5% | n=59
      Limitation: Rare signals
      
[V90] consec>=3 + shrink + score>=75
      60d hold | 10%=44.6% | 30%=18.8% | win=69.3% | n=1680
      Limitation: Moderate signals
""")

print("--- CHALLENGES ---")
print("""
[C01] Factor Mining    - Find new valid factors     [MEDIUM]
[C02] Overfitting Test  - Ensure strategy robustness [HARD]
[C03] Signal Freq      - High win rate + more signals [EXTREME]
[C04] Multi-Strategy   - Combine strategies          [HARD]
[C05] Real-time Data  - Intraday stock picking     [MEDIUM]
""")

print("=" * 70)
print("NEXT: Choose a challenge to start!")
print("=" * 70)
