"""八大细胞功能模块(M1-M8)的规范定义 + 物种支持矩阵 + 注册表。

设计:数据驱动(modules.py 定义 8 模块;每物种 brains/virtualcell/<species>/module_support.yaml
定义支持度)。模块是逻辑视图,内部映射到现有 engine/predictor,不为每模块造新引擎。"""
