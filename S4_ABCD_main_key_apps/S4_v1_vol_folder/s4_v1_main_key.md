# -------------------------
# S4_v1 3_獎最人氣球號預測
# 主要參數功能 分析。
VERSION = "S4_v1 3_獎最人氣球號預測 "

MODE = "backtest" # backtest / predict mode input
BACKTEST_DRAW_COUNT_LIST = [1]
WINDOW_DRAW_COUNT_LIST = [10] # 最少查詢 7 期
SELECT_GROUPS = 1,2,3,4 # Select 1,2,3,4 
COMB_MATCH_MODE = ">="
COMBINATION_TAKE_COUNT = 5


''' 
SELECT_GROUPS = 1,2,3,4 # Select 1,2,3,4 
COMB_MATCH_MODE = ">="
COMBINATION_TAKE_COUNT = 5

backtest:窗口期不包括核對期，預留核對預測
近 10期:2026-09-22,D2
近  9期:2026-09-26,C2
近  8期:2026-10-03,C3,[23,29,31],[8],[34],[] /> 5 球
近  7期:2026-10-06,C3,[29,31,*28],[34,36],[9],[] /> 5.5 球

'''

# False = ABCD 正常 / 
# True= ABCD 不分組 / 
# "sort", C D A B 那組強排前  。
LOTTO_LIST = "sort"
# "sort" / True C3，[23,29,31]，[8]，[34]
# "sort" / False [*5]，[18,19]，[24,31]，[40]
SORT_GROUPS_BY_COUNT = False
# --------------------
PRINT_BACKTEST_MODE = "detail"
PRIZE_OPTION = 3
PRIZE_PRINT_SHOW = False
