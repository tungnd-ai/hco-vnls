"""Hằng số khoa học đã khóa theo Bước 6–7 V5."""
from types import MappingProxyType

DIMENSION = 15
LEVELS = (0, 1, 2, 3)
LOWER, UPPER = 0.0, 3.0
EPSILON = 1e-12
RANDOM_SEED = 42
PARAMS = MappingProxyType(dict(nPop=100, MaxIt=500, w=0.65, w1=0.001, c1=1.4, c2=1.4))
