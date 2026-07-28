# ========================================
# Hylog 项目 - LLM 调用模块
# ========================================
# 此文件负责所有与大语言模型（LLM）的交互
# 包含：配置管理、LLM 调用封装、错误处理、成本控制、日志记录
# ========================================

# ----------------------------------------
# 导入标准库
# ----------------------------------------
import os  # 操作系统接口，用于读取环境变量
import json  # JSON 处理，用于解析 AI 返回的 JSON 数据
import time  # 时间处理，用于重试间隔
import logging  # 日志记录
from datetime import datetime  # 日期时间处理
from typing import Dict, List, Optional, Union, Generator, Any  # 类型注解
from dataclasses import dataclass, field  # 数据类装饰器
from enum import Enum  # 枚举类型
from pathlib import Path  # 路径处理

# ----------------------------------------
# 导入第三方库
# ----------------------------------------
from dotenv import load_dotenv  # 从 .env 文件加载环境变量
from openai import OpenAI  # OpenAI 官方 Python 库（兼容 DeepSeek）
from zhipuai import ZhipuAI  # 智谱 AI 官方 SDK（走套餐额度，不走余额）
import tiktoken  # Token 计数工具
import zhipuai  # 智谱 AI 官方 SDK（用于联网搜索和图片生成）

# ----------------------------------------
# 加载环境变量
# ----------------------------------------
# 从项目根目录的 .env 文件加载环境变量
load_dotenv()


# ========================================
# 第一部分：枚举和常量定义
# ========================================

class LLMProvider(Enum):
    """
    LLM 提供商枚举
    
    定义支持的 AI 提供商
    """
    ZHIPU = "zhipu"  # 智谱 AI（推荐，国内可用）
    # DEEPSEEK = "deepseek"  # DeepSeek（国内可用）
    # OPENAI = "openai"  # OpenAI（需要代理和国外信用卡）


class LLMFunction(Enum):
    """
    LLM 功能枚举
    
    定义不同的调用功能，用于成本分类统计
    """
    QUESTION_GENERATION = "question_generation"  # 问题生成
    PERSONALITY_ANALYSIS = "personality_analysis"  # 人格分析
    RESULT_EXPLANATION = "result_explanation"  # 结果解释
    TEXT_EMBEDDING = "text_embedding"  # 文本向量化
    CHARACTER_ANALYSIS = "character_analysis"  # 人物分析（联网搜索）
    IMAGE_GENERATION = "image_generation"  # 图片生成


class LLMErrorType(Enum):
    """
    LLM 错误类型枚举
    
    定义可能出现的错误类型
    """
    NETWORK_ERROR = "network_error"  # 网络错误
    API_ERROR = "api_error"  # API 错误
    TIMEOUT_ERROR = "timeout_error"  # 超时错误
    RATE_LIMIT_ERROR = "rate_limit_error"  # 限流错误
    PARAM_ERROR = "param_error"  # 参数错误
    JSON_PARSE_ERROR = "json_parse_error"  # JSON 解析错误
    COST_LIMIT_ERROR = "cost_limit_error"  # 成本上限错误
    UNKNOWN_ERROR = "unknown_error"  # 未知错误


# ----------------------------------------
# 价格配置（每 1M token 的价格，单位：元）
# ----------------------------------------
# 智谱 AI 价格（GLM-4，2024年数据，可能需要更新）
ZHIPU_PRICING = {
    "input": 100.0,  # 输入 token 价格：¥100/1M token
    "output": 100.0,  # 输出 token 价格：¥100/1M token
}

# DeepSeek 价格（2024年数据，可能需要更新）
DEEPSEEK_PRICING = {
    "input": 1.0,  # 输入 token 价格：¥1/1M token
    "output": 2.0,  # 输出 token 价格：¥2/1M token
}

# OpenAI 价格（GPT-3.5-turbo）
OPENAI_PRICING = {
    "input": 0.5,  # 输入 token 价格：$0.5/1M token（约 ¥3.5）
    "output": 1.5,  # 输出 token 价格：$1.5/1M token（约 ¥10.5）
}


# ========================================
# 第二部分：配置管理
# ========================================

@dataclass
class LLMConfig:
    """
    LLM 配置类
    
    管理所有 LLM 相关的配置参数
    """
    # ----------------------------------------
    # API 配置
    # ----------------------------------------
    api_key: str = ""  # API 密钥
    base_url: str = ""  # API 地址
    model: str = ""  # 模型名称
    provider: LLMProvider = LLMProvider.ZHIPU  # 提供商（默认智谱 AI）
    # provider: LLMProvider = LLMProvider.DEEPSEEK  # 提供商（默认 DeepSeek）
    
    # ----------------------------------------
    # 调用参数配置
    # ----------------------------------------
    temperature: float = 0.7  # 温度参数（0-1，值越大越随机）
    max_tokens: int = 2000  # 最大 token 数量
    timeout: int = 60  # 请求超时时间（秒）
    
    # ----------------------------------------
    # 重试配置
    # ----------------------------------------
    max_retries: int = 5  # 最大重试次数
    retry_base_interval: float = 1.0  # 重试基础间隔（秒）
    
    # ----------------------------------------
    # 成本控制配置
    # ----------------------------------------
    daily_cost_limit: float = 10.0  # 每日消费上限（元）
    monthly_cost_limit: float = 200.0  # 每月消费上限（元）
    
    # ----------------------------------------
    # 日志配置
    # ----------------------------------------
    log_level: str = "INFO"  # 日志级别
    log_retention_days: int = 30  # 日志保留天数
    log_max_size_mb: int = 10  # 单个日志文件最大大小（MB）
    
    # ----------------------------------------
    # 其他配置
    # ----------------------------------------
    record_history: bool = True  # 是否记录对话历史
    
    def load_from_env(self, provider: LLMProvider = LLMProvider.ZHIPU) -> None:
        """
        从环境变量加载配置
        
        参数:
            provider: LLM 提供商
        """
        # 设置提供商
        self.provider = provider
        
        # 根据提供商加载不同的配置
        if provider == LLMProvider.ZHIPU:
            # 加载智谱 AI 配置
            self.api_key = os.getenv("ZHIPU_API_KEY", "")
            self.base_url = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
            self.model = os.getenv("ZHIPU_MODEL", "glm-4")
        elif provider == LLMProvider.DEEPSEEK:
            # 加载 DeepSeek 配置
            self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
            self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
            self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        else:
            # 加载 OpenAI 配置
            self.api_key = os.getenv("OPENAI_API_KEY", "")
            self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        # 加载通用配置
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        self.timeout = int(os.getenv("LLM_TIMEOUT", "60"))
        
        # 加载成本控制配置
        self.daily_cost_limit = float(os.getenv("DAILY_COST_LIMIT", "10"))
        self.monthly_cost_limit = float(os.getenv("MONTHLY_COST_LIMIT", "200"))
        
        # 加载日志配置
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_retention_days = int(os.getenv("LOG_RETENTION_DAYS", "30"))
        self.log_max_size_mb = int(os.getenv("LOG_MAX_SIZE_MB", "10"))
    
    def validate(self) -> bool:
        """
        验证配置是否有效
        
        返回:
            配置是否有效
        """
        # 检查 API Key 是否存在
        if not self.api_key:
            raise ValueError(f"{self.provider.value.upper()}_API_KEY 未配置！请在 .env 文件中设置。")
        
        # 检查温度参数范围
        if not 0 <= self.temperature <= 1:
            raise ValueError(f"温度参数必须在 0-1 之间，当前值：{self.temperature}")
        
        # 检查最大 token 数量
        if self.max_tokens <= 0:
            raise ValueError(f"最大 token 数量必须大于 0，当前值：{self.max_tokens}")
        
        # 检查超时时间
        if self.timeout <= 0:
            raise ValueError(f"超时时间必须大于 0，当前值：{self.timeout}")
        
        return True


# ========================================
# 第三部分：成本控制
# ========================================

@dataclass
class UsageRecord:
    """
    使用记录类
    
    记录单次 API 调用的使用情况
    """
    timestamp: str  # 时间戳
    function: str  # 功能类型
    input_tokens: int  # 输入 token 数
    output_tokens: int  # 输出 token 数
    total_tokens: int  # 总 token 数
    cost: float  # 成本（元）
    model: str  # 使用的模型
    success: bool  # 是否成功


class CostController:
    """
    成本控制器
    
    管理 API 调用的成本监控和控制
    """
    
    COST_FILE = Path("logs/cost_stats.json")  # 成本统计文件路径
    
    def __init__(self, config: LLMConfig):
        """
        初始化成本控制器
        
        参数:
            config: LLM 配置
        """
        self.config = config  # 配置对象
        self.usage_records: List[UsageRecord] = []  # 使用记录列表
        self.daily_cost: float = 0.0  # 今日消费
        self.monthly_cost: float = 0.0  # 本月消费
        self.function_costs: Dict[str, float] = {}  # 按功能分类的成本
        
        # 根据提供商选择价格配置
        if config.provider == LLMProvider.ZHIPU:
            self.pricing = ZHIPU_PRICING
        elif config.provider == LLMProvider.DEEPSEEK:
            self.pricing = DEEPSEEK_PRICING
        else:
            self.pricing = OPENAI_PRICING
        
        # 从文件加载已有数据
        self._load_from_file()
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        计算调用成本
        
        参数:
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
        
        返回:
            成本（元）
        """
        # 计算输入成本
        input_cost = (input_tokens / 1000000) * self.pricing["input"]
        
        # 计算输出成本
        output_cost = (output_tokens / 1000000) * self.pricing["output"]
        
        # 返回总成本
        return input_cost + output_cost
    
    def record_usage(
        self,
        function: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
        success: bool = True
    ) -> UsageRecord:
        """
        记录使用情况
        
        参数:
            function: 功能类型
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            model: 使用的模型
            success: 是否成功
        
        返回:
            使用记录
        """
        # 计算成本
        cost = self.calculate_cost(input_tokens, output_tokens)
        
        # 创建使用记录
        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            function=function,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            model=model,
            success=success
        )
        
        # 添加到记录列表
        self.usage_records.append(record)
        
        # 更新累计成本
        self.daily_cost += cost
        self.monthly_cost += cost
        
        # 更新按功能分类的成本
        if function not in self.function_costs:
            self.function_costs[function] = 0.0
        self.function_costs[function] += cost
        
        # 保存到文件
        self._save_to_file()
        
        return record
    
    def check_limit(self) -> bool:
        """
        检查是否超过成本上限
        
        返回:
            是否可以继续调用（True = 可以，False = 超过上限）
        """
        # 检查每日上限
        if self.daily_cost >= self.config.daily_cost_limit:
            return False
        
        # 检查每月上限
        if self.monthly_cost >= self.config.monthly_cost_limit:
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取使用统计
        
        返回:
            统计数据字典
        """
        return {
            "daily_cost": self.daily_cost,  # 今日消费
            "monthly_cost": self.monthly_cost,  # 本月消费
            "daily_limit": self.config.daily_cost_limit,  # 每日上限
            "monthly_limit": self.config.monthly_cost_limit,  # 每月上限
            "total_calls": len(self.usage_records),  # 总调用次数
            "function_costs": self.function_costs,  # 按功能分类的成本
        }
    
    def reset_daily(self) -> None:
        """
        重置每日统计
        
        每天凌晨调用此方法
        """
        self.daily_cost = 0.0
        self._save_to_file()
    
    def reset_monthly(self) -> None:
        """
        重置每月统计
        
        每月 1 号调用此方法
        """
        self.monthly_cost = 0.0
        self.function_costs = {}
        self._save_to_file()
    
    def _load_from_file(self) -> None:
        """
        从文件加载成本统计数据
        """
        # 确保目录存在
        self.COST_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        if self.COST_FILE.exists():
            try:
                with open(self.COST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 检查日期，如果不是今天则重置每日统计
                saved_date = data.get("date", "")
                today = datetime.now().strftime("%Y-%m-%d")
                
                if saved_date != today:
                    self.daily_cost = 0.0
                else:
                    self.daily_cost = data.get("daily_cost", 0.0)
                
                # 检查月份，如果不是本月则重置每月统计
                saved_month = data.get("month", "")
                current_month = datetime.now().strftime("%Y-%m")
                
                if saved_month != current_month:
                    self.monthly_cost = 0.0
                    self.function_costs = {}
                else:
                    self.monthly_cost = data.get("monthly_cost", 0.0)
                    self.function_costs = data.get("function_costs", {})
                
            except Exception:
                # 文件读取失败，使用默认值
                self.daily_cost = 0.0
                self.monthly_cost = 0.0
                self.function_costs = {}
    
    def _save_to_file(self) -> None:
        """
        保存成本统计数据到文件
        """
        # 确保目录存在
        self.COST_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "month": datetime.now().strftime("%Y-%m"),
            "daily_cost": self.daily_cost,
            "monthly_cost": self.monthly_cost,
            "function_costs": self.function_costs,
        }
        
        try:
            with open(self.COST_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 保存失败不影响正常运行


# ========================================
# 第四部分：日志记录
# ========================================

class LLMLogger:
    """
    LLM 日志记录器
    
    记录 API 调用的请求、响应、错误等信息
    """
    
    def __init__(self, config: LLMConfig):
        """
        初始化日志记录器
        
        参数:
            config: LLM 配置
        """
        self.config = config
        
        # 创建日志目录
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 配置日志记录器
        self.logger = logging.getLogger("llm")
        self.logger.setLevel(getattr(logging, config.log_level))
        
        # 如果还没有处理器，添加处理器
        if not self.logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
            
            # 文件处理器
            log_file = self.log_dir / f"llm_{datetime.now().strftime('%Y-%m-%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
    
    def log_request(
        self,
        messages: List[Dict],
        function: str,
        model: str,
        **kwargs
    ) -> None:
        """
        记录请求日志
        
        参数:
            messages: 消息列表
            function: 功能类型
            model: 模型名称
            **kwargs: 其他参数
        """
        # 构建日志消息
        log_msg = f"[REQUEST] Function: {function}, Model: {model}"
        
        # 记录消息内容（简化版，避免日志过长）
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # 截断过长的内容
            if len(content) > 100:
                content = content[:100] + "..."
            log_msg += f"\n  [{i}] {role}: {content}"
        
        # 记录其他参数
        for key, value in kwargs.items():
            log_msg += f"\n  {key}: {value}"
        
        self.logger.info(log_msg)
    
    def log_response(
        self,
        response: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        elapsed_time: float
    ) -> None:
        """
        记录响应日志
        
        参数:
            response: 响应内容
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            cost: 成本
            elapsed_time: 耗时（秒）
        """
        # 截断过长的响应
        if len(response) > 200:
            response_preview = response[:200] + "..."
        else:
            response_preview = response
        
        log_msg = (
            f"[RESPONSE] Tokens: {input_tokens}+{output_tokens}={input_tokens + output_tokens}, "
            f"Cost: ¥{cost:.6f}, Time: {elapsed_time:.2f}s\n"
            f"  Content: {response_preview}"
        )
        
        self.logger.info(log_msg)
    
    def log_error(
        self,
        error_type: LLMErrorType,
        error_msg: str,
        retry_count: int = 0
    ) -> None:
        """
        记录错误日志
        
        参数:
            error_type: 错误类型
            error_msg: 错误消息
            retry_count: 重试次数
        """
        log_msg = f"[ERROR] Type: {error_type.value}, Retry: {retry_count}, Message: {error_msg}"
        self.logger.error(log_msg)
    
    def log_cost_warning(self, current_cost: float, limit: float, period: str) -> None:
        """
        记录成本预警日志
        
        参数:
            current_cost: 当前成本
            limit: 上限
            period: 周期（daily/monthly）
        """
        log_msg = f"[COST WARNING] {period} cost ¥{current_cost:.2f} approaching limit ¥{limit:.2f}"
        self.logger.warning(log_msg)


# ========================================
# 第五部分：错误处理
# ========================================

class LLMError(Exception):
    """
    LLM 错误类
    
    自定义异常类，包含错误类型和详细信息
    """
    
    def __init__(self, error_type: LLMErrorType, message: str, retry_count: int = 0):
        """
        初始化错误
        
        参数:
            error_type: 错误类型
            message: 错误消息
            retry_count: 重试次数
        """
        self.error_type = error_type
        self.message = message
        self.retry_count = retry_count
        super().__init__(f"[{error_type.value}] {message}")
    
    def is_retryable(self) -> bool:
        """
        判断错误是否可重试
        
        返回:
            是否可重试
        """
        # 可重试的错误类型
        retryable_types = {
            LLMErrorType.NETWORK_ERROR,
            LLMErrorType.TIMEOUT_ERROR,
            LLMErrorType.RATE_LIMIT_ERROR,
        }
        return self.error_type in retryable_types


def classify_error(error: Exception) -> LLMErrorType:
    """
    分类错误类型
    
    参数:
        error: 异常对象
    
    返回:
        错误类型
    """
    error_str = str(error).lower()
    
    # 网络错误
    if "connection" in error_str or "network" in error_str:
        return LLMErrorType.NETWORK_ERROR
    
    # 超时错误
    if "timeout" in error_str:
        return LLMErrorType.TIMEOUT_ERROR
    
    # 限流错误
    if "rate limit" in error_str or "429" in error_str:
        return LLMErrorType.RATE_LIMIT_ERROR
    
    # API 错误
    if "api" in error_str or "500" in error_str or "502" in error_str or "503" in error_str:
        return LLMErrorType.API_ERROR
    
    # 参数错误
    if "invalid" in error_str or "param" in error_str or "400" in error_str:
        return LLMErrorType.PARAM_ERROR
    
    # 未知错误
    return LLMErrorType.UNKNOWN_ERROR


# ========================================
# 第六部分：Token 计数
# ========================================

class TokenCounter:
    """
    Token 计数器
    
    计算消息的 token 数量
    """
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        初始化 Token 计数器
        
        参数:
            model: 模型名称
        """
        self.model = model
        
        # 尝试获取编码器
        try:
            # 对于 DeepSeek，使用 cl100k_base 编码（与 GPT-3.5/4 相同）
            if "deepseek" in model.lower():
                self.encoding = tiktoken.get_encoding("cl100k_base")
            else:
                self.encoding = tiktoken.encoding_for_model(model)
        except Exception:
            # 如果模型不支持，使用默认编码
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的 token 数量
        
        参数:
            text: 文本内容
        
        返回:
            token 数量
        """
        return len(self.encoding.encode(text))
    
    def count_messages_tokens(self, messages: List[Dict]) -> int:
        """
        计算消息列表的 token 数量
        
        参数:
            messages: 消息列表
        
        返回:
            token 数量
        """
        total_tokens = 0
        
        # 遍历每条消息
        for message in messages:
            # 每条消息有固定的 token 开销
            total_tokens += 4  # 消息格式开销
            
            # 计算每个字段的 token
            for key, value in message.items():
                total_tokens += len(self.encoding.encode(str(value)))
        
        # 加上消息列表的固定开销
        total_tokens += 2
        
        return total_tokens


# ========================================
# 第七部分：LLM 客户端
# ========================================

class LLMClient:
    """
    LLM 客户端
    
    封装所有 LLM 调用功能
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化 LLM 客户端
        
        参数:
            config: LLM 配置（可选，默认从环境变量加载）
        """
        # 加载配置
        if config is None:
            config = LLMConfig()
            config.load_from_env(LLMProvider.ZHIPU)  # 默认使用智谱 AI
            # config.load_from_env(LLMProvider.DEEPSEEK)  # 默认使用 DeepSeek
        
        # 验证配置
        config.validate()
        self.config = config
        
        # 初始化智谱官方 SDK 客户端（走套餐额度）
        # 注：ZhipuAI 默认 base_url 即智谱官方地址，无需显式传 base_url
        self.client = ZhipuAI(
            api_key=config.api_key,
            timeout=config.timeout,
        )
        
        # 初始化成本控制器
        self.cost_controller = CostController(config)
        
        # 初始化日志记录器
        self.logger = LLMLogger(config)
        
        # 初始化 Token 计数器
        self.token_counter = TokenCounter(config.model)
    
    # ----------------------------------------
    # 基础调用方法
    # ----------------------------------------
    
    def chat(
        self,
        messages: List[Dict],
        function: str = LLMFunction.PERSONALITY_ANALYSIS.value,
        **kwargs
    ) -> str:
        """
        对话补全（非流式）
        
        参数:
            messages: 消息列表
            function: 功能类型（用于成本统计）
            **kwargs: 其他参数（temperature, max_tokens 等）
        
        返回:
            AI 的回复文本
        
        异常:
            LLMError: 调用失败
        """
        # 检查成本上限
        if not self.cost_controller.check_limit():
            raise LLMError(
                LLMErrorType.COST_LIMIT_ERROR,
                f"已达到成本上限：每日 ¥{self.config.daily_cost_limit}，每月 ¥{self.config.monthly_cost_limit}"
            )
        
        # 合并参数
        temperature = kwargs.get("temperature", self.config.temperature)
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        
        # 记录请求日志
        self.logger.log_request(
            messages=messages,
            function=function,
            model=self.config.model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # 重试机制
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retries:
            try:
                # 记录开始时间
                start_time = time.time()
                
                # 调用 API
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                # 计算耗时
                elapsed_time = time.time() - start_time
                
                # 提取响应内容
                content = response.choices[0].message.content
                
                # 检查空响应
                if not content or len(content.strip()) == 0:
                    self.logger.log_error(LLMErrorType.API_ERROR, "AI返回空内容")
                    raise LLMError(LLMErrorType.API_ERROR, "AI返回空内容，请稍后重试")
                
                # 获取 token 使用量
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                
                # 记录使用情况
                record = self.cost_controller.record_usage(
                    function=function,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model=self.config.model,
                    success=True
                )
                
                # 记录响应日志
                self.logger.log_response(
                    response=content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=record.cost,
                    elapsed_time=elapsed_time
                )
                
                return content
                
            except Exception as e:
                # 分类错误
                error_type = classify_error(e)
                last_error = LLMError(error_type, str(e), retry_count)
                
                # 记录错误日志
                self.logger.log_error(error_type, str(e), retry_count)
                
                # 判断是否可重试
                if last_error.is_retryable() and retry_count < self.config.max_retries:
                    retry_count += 1
                    
                    # 计算重试间隔（递增）
                    interval = self.config.retry_base_interval * (2 ** retry_count)
                    time.sleep(interval)
                else:
                    # 不可重试或超过最大重试次数
                    break
        
        # 记录失败的使用情况
        input_tokens = self.token_counter.count_messages_tokens(messages)
        self.cost_controller.record_usage(
            function=function,
            input_tokens=input_tokens,
            output_tokens=0,
            model=self.config.model,
            success=False
        )
        
        # 抛出最后的错误
        raise last_error
    
    def chat_stream(
        self,
        messages: List[Dict],
        function: str = LLMFunction.QUESTION_GENERATION.value,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        对话补全（流式）
        
        参数:
            messages: 消息列表
            function: 功能类型（用于成本统计）
            **kwargs: 其他参数
        
        返回:
            生成器，逐字返回 AI 的回复
        
        异常:
            LLMError: 调用失败
        """
        # 检查成本上限
        if not self.cost_controller.check_limit():
            raise LLMError(
                LLMErrorType.COST_LIMIT_ERROR,
                f"已达到成本上限：每日 ¥{self.config.daily_cost_limit}，每月 ¥{self.config.monthly_cost_limit}"
            )
        
        # 合并参数
        temperature = kwargs.get("temperature", self.config.temperature)
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        
        # 记录请求日志
        self.logger.log_request(
            messages=messages,
            function=function,
            model=self.config.model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        # 重试机制
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retries:
            try:
                # 记录开始时间
                start_time = time.time()
                
                # 调用 API（流式）
                stream = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )
                
                # 收集完整响应（用于统计）
                full_content = ""
                input_tokens = self.token_counter.count_messages_tokens(messages)
                output_tokens = 0
                
                # 逐块返回内容
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        output_tokens += 1  # 近似计数
                        yield content
                
                # 计算耗时
                elapsed_time = time.time() - start_time
                
                # 记录使用情况
                record = self.cost_controller.record_usage(
                    function=function,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model=self.config.model,
                    success=True
                )
                
                # 记录响应日志
                self.logger.log_response(
                    response=full_content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=record.cost,
                    elapsed_time=elapsed_time
                )
                
                return
                
            except Exception as e:
                # 分类错误
                error_type = classify_error(e)
                last_error = LLMError(error_type, str(e), retry_count)
                
                # 记录错误日志
                self.logger.log_error(error_type, str(e), retry_count)
                
                # 判断是否可重试
                if last_error.is_retryable() and retry_count < self.config.max_retries:
                    retry_count += 1
                    
                    # 计算重试间隔（递增）
                    interval = self.config.retry_base_interval * (2 ** retry_count)
                    time.sleep(interval)
                else:
                    # 不可重试或超过最大重试次数
                    break
        
        # 抛出最后的错误
        raise last_error
    
    # ----------------------------------------
    # 高级调用方法
    # ----------------------------------------
    
    def analyze_personality(
        self,
        user_answer: str,
        current_ocean: Dict[str, float],
        question_dimension: str
    ) -> Dict[str, float]:
        """
        分析用户回答，返回 OCEAN 影响值
        
        参数:
            user_answer: 用户的回答
            current_ocean: 当前的 OCEAN 分数
            question_dimension: 问题维度
        
        返回:
            OCEAN 影响值字典，如 {"O": 0.02, "C": 0, "E": -0.08, "A": 0.01, "N": 0}
            或包含 skipped 字段的特殊返回
        """
        # 输入验证
        if not user_answer or len(user_answer.strip()) == 0:
            return {
                "skipped": True,
                "reason": "empty",
                "guidance": "请回答一下这个问题，这样我能更好地了解你。",
                "O": 0, "C": 0, "E": 0, "A": 0, "N": 0
            }
        
        if len(user_answer) > 100:
            return {
                "skipped": True,
                "reason": "too_long",
                "guidance": "你的回答有点长，能简单概括一下吗？",
                "O": 0, "C": 0, "E": 0, "A": 0, "N": 0
            }
        
        # 构建 system prompt
        system_prompt = """你是一个人格分析专家。根据用户的回答，分析其对 OCEAN 五维人格的影响。

OCEAN 五维人格：
- O (开放性 Openness)：好奇心、创造力、开放新体验
- C (责任心 Conscientiousness)：自律、责任感、目标导向
- E (外向性 Extraversion)：社交活跃、精力充沛、乐观
- A (宜人性 Agreeableness)：信任、合作、善良
- N (神经质 Neuroticism)：情绪不稳定、焦虑、敏感

## 正常情况
当用户回答与问题相关时，返回：
{"O": 数值, "C": 数值, "E": 数值, "A": 数值, "N": 数值}

变化值范围：-0.08 到 0.08，无明显影响时设为 0。

## 关键原则：精准而非笼统
1. 一次回答通常只明显影响 1~2 个维度，其余维度应设为 0。不要对所有维度都给非零值。
2. 绝对禁止对 5 个维度都输出相同的非零值（如全 0.1 或全 -0.05），这是无效分析。
3. 只根据回答中明确体现的特质给分，牵强附会的影响一律设为 0。
4. 数值要体现强弱：强烈特质用 ±0.06~0.08，轻微特质用 ±0.02~0.04。

## 特殊情况处理
当用户出现以下情况时，不要强行分析人格，而是返回：
{"skipped": true, "reason": "原因", "guidance": "引导语"}

特殊情况包括：
1. 回答与问题完全无关（如答非所问、转移话题）
2. 拒绝回答（如"不想说"、"跳过"、"不知道"）
3. 回答过于简短或无意义（如"嗯"、"随便"、"不知道"）
4. 表达困惑或不适（如"不太理解"、"这个问题让我不舒服"）
5. 情绪负面或抵触

reason 可选值：irrelevant（无关）、refused（拒绝）、unclear（不明确）、uncomfortable（不适）、negative（负面）
guidance 应该是友好的引导语，帮助用户继续对话，如"没关系，我们换个话题聊聊..."

注意：
1. 只返回 JSON，不要有其他内容
2. 仔细判断用户回答是否有效，不要过度解读简短回答"""
        
        # 构建 user prompt
        user_prompt = f"""用户回答：{user_answer}

当前问题维度：{question_dimension}

当前 OCEAN 分数：
- O (开放性): {current_ocean.get('O', 0.5):.2f}
- C (责任心): {current_ocean.get('C', 0.5):.2f}
- E (外向性): {current_ocean.get('E', 0.5):.2f}
- A (宜人性): {current_ocean.get('A', 0.5):.2f}
- N (神经质): {current_ocean.get('N', 0.5):.2f}

请分析这个回答对 OCEAN 各维度的影响。"""
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 调用 API
        response = self.chat(
            messages=messages,
            function=LLMFunction.PERSONALITY_ANALYSIS.value
        )
        
        # 解析 JSON
        try:
            # 尝试提取 JSON（处理 AI 可能返回的额外内容）
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
            else:
                result = json.loads(response)
            
            # 检查是否为特殊情况（用户回答无效）
            if result.get("skipped") == True:
                # 返回包含引导信息的结构
                return {
                    "skipped": True,
                    "reason": result.get("reason", "unclear"),
                    "guidance": result.get("guidance", "没关系，我们换个话题聊聊吧。"),
                    "O": 0, "C": 0, "E": 0, "A": 0, "N": 0
                }
            
            # 验证并限制范围（与 prompt 中的 ±0.08 保持一致）
            for dim in ["O", "C", "E", "A", "N"]:
                if dim in result:
                    result[dim] = max(-0.08, min(0.08, float(result[dim])))
                else:
                    result[dim] = 0.0
            
            return result
            
        except json.JSONDecodeError as e:
            # JSON 解析失败
            self.logger.log_error(LLMErrorType.JSON_PARSE_ERROR, str(e))
            # 返回默认值
            return {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    
    def analyze_character(
        self,
        character_name: str,
        source: str,
        era: str = ""
    ) -> Dict[str, Any]:
        """
        分析人物，返回 OCEAN 分数和所有展示内容
        
        此方法使用联网搜索功能，让 AI 搜索人物资料后进行分析。
        
        参数:
            character_name: 人物名称
            source: 来源（历史）
            era: 时代/年代（历史人物必填，如"唐朝"、"三国"）
        
        返回:
            包含人物所有信息的字典：
            {
                "O": 0.72, "C": 0.65, "E": 0.45, "A": 0.58, "N": 0.32,
                "description": "人物简介...",
                "tags": ["智慧", "忠诚", "谨慎"],
                "quote": "语录/名言/成语/评价",
                "personality_keyword": "智慧谨慎型",
                "classic_events": "经典场景/事件",
                "fun_facts": "趣味冷知识",
                "advice": "性格建议",
                "related_books": "相关书籍"
            }
        """
        # 构建 system prompt（强调联网搜索、只分析真实历史人物、阅读足够多资料）
        system_prompt = """你是一个人格分析专家和史学研究助手。请分析指定人物的人格特质。

## 重要要求
1. **必须使用联网搜索功能**，搜索该人物的相关资料
2. **只分析中国历史上真实存在的人物**（清朝或之前），不要分析虚构人物、神话人物、文学角色、影视角色
3. **优先阅读权威资料**：如 Wikipedia、百度百科、官方传记、学术文献
4. **再阅读其他来源辅助判断**：如新闻报道、评论文章、学术研究
5. **尽可能阅读足够多的资料**（建议 2000-5000 字），确保分析准确
6. **不要凭空猜测**，所有分析必须基于搜索到的资料

## OCEAN 五维人格说明
- O (开放性 Openness)：好奇心、创造力、开放新体验、艺术兴趣
- C (责任心 Conscientiousness)：自律、责任感、目标导向、计划性
- E (外向性 Extraversion)：社交活跃、精力充沛、乐观、 assertiveness
- A (宜人性 Agreeableness)：信任、合作、善良、同理心
- N (神经质 Neuroticism)：情绪不稳定、焦虑、敏感、冲动

分数范围 0.0-1.0：
- 0.0-0.3：该维度特质很弱
- 0.3-0.5：该维度特质较弱
- 0.5-0.7：该维度特质中等
- 0.7-0.9：该维度特质较强
- 0.9-1.0：该维度特质很强

## 输出格式（JSON）
请严格按照以下格式输出，不要有其他内容：

```json
{
    "O": 0.72,
    "C": 0.65,
    "E": 0.45,
    "A": 0.58,
    "N": 0.32,
    "description": "人物简介生平（100-200字，简洁概括人物的主要经历和特点）",
    "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"],
    "quote": "语录/名言/成语/评价（可以是人物自己的名言，或他人对他的评价，或相关成语）",
    "personality_keyword": "性格关键词（如'智慧谨慎型'、'豪迈奔放型'，用4-6个字概括）",
    "classic_events": "经典场景/事件（描述1-3个代表性事件，每个事件50字左右）",
    "fun_facts": "趣味冷知识（有趣的、不为人知的小知识，50-100字）",
    "advice": "性格建议（基于人物性格，给现代人的生活建议，50-100字）",
    "related_books": "相关书籍（推荐1-3本了解该人物的书籍，包括书名和简短说明）"
}
```

## 注意事项
1. 只返回 JSON，不要有其他内容
2. 所有内容必须基于搜索到的资料，不要编造
3. 如果某些信息找不到，可以写"暂无相关资料"
4. 标签要具体、有代表性，不要过于笼统"""
        
        # 构建 user prompt
        era_info = f"，时代：{era}" if era else ""
        user_prompt = f"""请分析以下人物的人格特质：

人物名称：{character_name}
来源：{source}{era_info}

请使用联网搜索功能，搜索该人物的资料，然后进行分析。"""
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 调用 API（使用联网搜索）
        # 使用智谱官方 SDK 实现联网搜索功能
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 记录请求日志
            self.logger.log_request(
                messages=messages,
                function=LLMFunction.CHARACTER_ANALYSIS.value,
                model=self.config.model,
                web_search=True
            )
            
            # 使用智谱官方 SDK 调用（支持联网搜索）
            # 智谱 SDK 的联网搜索通过 tools 参数实现
            zhipu_client = zhipuai.ZhipuAI(api_key=self.config.api_key)
            
            response = zhipu_client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=0.3,
                max_tokens=3000,
                tools=[{
                    "type": "web_search",
                    "web_search": {"search_result": True}
                }]
            )
            
            # 计算耗时
            elapsed_time = time.time() - start_time
            
            # 提取响应内容
            content = response.choices[0].message.content
            
            # 检查空响应
            if not content or len(content.strip()) == 0:
                self.logger.log_error(LLMErrorType.API_ERROR, "AI返回空内容")
                raise LLMError(LLMErrorType.API_ERROR, "AI返回空内容，请稍后重试")
            
            # 获取 token 使用量
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # 记录使用情况
            record = self.cost_controller.record_usage(
                function=LLMFunction.CHARACTER_ANALYSIS.value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=self.config.model,
                success=True
            )
            
            # 记录响应日志
            self.logger.log_response(
                response=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=record.cost,
                elapsed_time=elapsed_time
            )
            
            # 解析 JSON
            try:
                # 尝试提取 JSON
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    result = json.loads(content)
                
                # 验证 OCEAN 分数范围
                for dim in ["O", "C", "E", "A", "N"]:
                    if dim in result:
                        result[dim] = max(0.0, min(1.0, float(result[dim])))
                    else:
                        result[dim] = 0.5  # 默认值
                
                # 验证其他字段
                if "description" not in result:
                    result["description"] = f"{character_name}是{source}中的重要人物。"
                if "tags" not in result:
                    result["tags"] = []
                if "quote" not in result:
                    result["quote"] = ""
                if "personality_keyword" not in result:
                    result["personality_keyword"] = ""
                if "classic_events" not in result:
                    result["classic_events"] = ""
                if "fun_facts" not in result:
                    result["fun_facts"] = ""
                if "advice" not in result:
                    result["advice"] = ""
                if "related_books" not in result:
                    result["related_books"] = ""
                
                return result
                
            except json.JSONDecodeError as e:
                self.logger.log_error(LLMErrorType.JSON_PARSE_ERROR, str(e))
                # 返回默认值
                return {
                    "O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5,
                    "description": f"{character_name}是{source}中的重要人物。",
                    "tags": [],
                    "quote": "",
                    "personality_keyword": "",
                    "classic_events": "",
                    "fun_facts": "",
                    "advice": "",
                    "related_books": "",
                    "parse_error": True
                }
                
        except Exception as e:
            # 分类错误
            error_type = classify_error(e)
            self.logger.log_error(error_type, str(e))
            raise LLMError(error_type, str(e))
    
    def generate_character_image(
        self,
        character_name: str,
        description: str,
        source: str,
        save_dir: str = "data/characters/images"
    ) -> str:
        """
        生成人物图片
        
        使用智谱 CogView API 生成人物图片，并保存到本地。
        
        参数:
            character_name: 人物名称
            description: 人物描述（用于生成图片的提示词）
            source: 来源（历史）
            save_dir: 图片保存目录
        
        返回:
            图片的本地路径
        """
        # 构建图片生成提示词
        prompt = f"""一张{source}人物"{character_name}"的肖像画。
人物特点：{description}
风格：中国传统水墨画风格，简洁典雅，突出人物性格特点，适合作为头像使用。"""
        
        # 记录请求日志
        self.logger.log_request(
            messages=[{"role": "user", "content": prompt[:100]}],
            function=LLMFunction.IMAGE_GENERATION.value,
            model="cogview-3"
        )
        
        try:
            # 使用智谱官方 SDK 调用图片生成 API
            zhipu_client = zhipuai.ZhipuAI(api_key=self.config.api_key)
            
            response = zhipu_client.chat.completions.create(
                model="cogview-3",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50
            )
            
            # 获取图片 URL
            content = response.choices[0].message.content
            # 智谱图片生成可能返回图片 URL 或 base64 数据
            image_url = content
            
            # 下载图片到本地
            import requests
            from pathlib import Path
            
            # 确保保存目录存在
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名（使用人物名称）
            # 替换特殊字符，避免文件名问题
            safe_name = character_name.replace("/", "_").replace("\\", "_")
            file_name = f"{safe_name}.png"
            file_path = save_path / file_name
            
            # 下载图片
            img_response = requests.get(image_url, timeout=30)
            if img_response.status_code == 200:
                # 保存图片
                with open(file_path, "wb") as f:
                    f.write(img_response.content)
                
                # 记录使用情况（图片生成按次计费）
                self.cost_controller.record_usage(
                    function=LLMFunction.IMAGE_GENERATION.value,
                    input_tokens=len(prompt),
                    output_tokens=0,
                    model="cogview-3",
                    success=True
                )
                
                # 返回本地路径
                return str(file_path)
            else:
                # 下载失败
                error_msg = f"图片下载失败，状态码：{img_response.status_code}"
                self.logger.log_error(LLMErrorType.API_ERROR, error_msg)
                raise LLMError(LLMErrorType.API_ERROR, error_msg)
            
        except Exception as e:
            error_type = classify_error(e)
            self.logger.log_error(error_type, str(e))
            raise LLMError(error_type, str(e))
    
    def embed_text(self, text: str) -> List[float]:
        """
        文本向量化
        
        参数:
            text: 要向量化的文本
        
        返回:
            向量列表
        """
        # 记录请求日志
        self.logger.log_request(
            messages=[{"role": "user", "content": text[:100]}],
            function=LLMFunction.TEXT_EMBEDDING.value,
            model="text-embedding-ada-002"
        )
        
        try:
            # 调用 embedding API
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            
            # 提取向量
            vector = response.data[0].embedding
            
            # 记录使用情况
            self.cost_controller.record_usage(
                function=LLMFunction.TEXT_EMBEDDING.value,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=0,
                model="text-embedding-ada-002",
                success=True
            )
            
            return vector
            
        except Exception as e:
            # 记录错误
            error_type = classify_error(e)
            self.logger.log_error(error_type, str(e))
            raise LLMError(error_type, str(e))
    
    # ----------------------------------------
    # 工具方法
    # ----------------------------------------
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的 token 数量
        
        参数:
            text: 文本内容
        
        返回:
            token 数量
        """
        return self.token_counter.count_tokens(text)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        获取使用统计
        
        返回:
            统计数据
        """
        return self.cost_controller.get_stats()
    
    def switch_provider(self, provider: LLMProvider) -> None:
        """
        切换 AI 提供商
        
        参数:
            provider: 新的提供商
        """
        # 重新加载配置
        self.config.load_from_env(provider)
        self.config.validate()
        
        # 重新初始化智谱 SDK 客户端
        self.client = ZhipuAI(
            api_key=self.config.api_key,
            timeout=self.config.timeout,
        )
        
        # 更新成本控制器
        self.cost_controller = CostController(self.config)
        
        # 更新 Token 计数器
        self.token_counter = TokenCounter(self.config.model)
        
        # 记录日志
        self.logger.logger.info(f"Switched to provider: {provider.value}")


# ========================================
# 第八部分：便捷函数
# ========================================

# 全局客户端实例（懒加载）
_client: Optional[LLMClient] = None


def get_client() -> LLMClient:
    """
    获取全局 LLM 客户端实例
    
    返回:
        LLM 客户端
    """
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def chat(messages: List[Dict], **kwargs) -> str:
    """
    对话补全（便捷函数）
    
    参数:
        messages: 消息列表
        **kwargs: 其他参数
    
    返回:
        AI 的回复
    """
    return get_client().chat(messages, **kwargs)


def chat_stream(messages: List[Dict], **kwargs) -> Generator[str, None, None]:
    """
    对话补全流式（便捷函数）
    
    参数:
        messages: 消息列表
        **kwargs: 其他参数
    
    返回:
        生成器
    """
    yield from get_client().chat_stream(messages, **kwargs)


def analyze_personality(
    user_answer: str,
    current_ocean: Dict[str, float],
    question_dimension: str
) -> Dict[str, float]:
    """
    分析人格（便捷函数）
    
    参数:
        user_answer: 用户回答
        current_ocean: 当前 OCEAN 分数
        question_dimension: 问题维度
    
    返回:
        OCEAN 影响值
    """
    return get_client().analyze_personality(user_answer, current_ocean, question_dimension)


def embed_text(text: str) -> List[float]:
    """
    文本向量化（便捷函数）
    
    参数:
        text: 文本内容
    
    返回:
        向量
    """
    return get_client().embed_text(text)


def count_tokens(text: str) -> int:
    """
    计算 token 数量（便捷函数）
    
    参数:
        text: 文本内容
    
    返回:
        token 数量
    """
    return get_client().count_tokens(text)


def get_usage_stats() -> Dict[str, Any]:
    """
    获取使用统计（便捷函数）
    
    返回:
        统计数据
    """
    return get_client().get_usage_stats()


def analyze_character(
    character_name: str,
    source: str,
    era: str = ""
) -> Dict[str, Any]:
    """
    分析人物（便捷函数）
    
    使用联网搜索功能，让 AI 搜索人物资料后进行分析。
    
    参数:
        character_name: 人物名称
        source: 来源（历史）
        era: 时代/年代（历史人物必填，如"唐朝"、"三国"）

    返回:
        包含人物所有信息的字典
    """
    return get_client().analyze_character(character_name, source, era)


def generate_character_image(
    character_name: str,
    description: str,
    source: str,
    save_dir: str = "data/characters/images"
) -> str:
    """
    生成人物图片（便捷函数）
    
    使用智谱 CogView API 生成人物图片，并保存到本地。
    
    参数:
        character_name: 人物名称
        description: 人物描述
        source: 来源（历史）
        save_dir: 图片保存目录
    
    返回:
        图片的本地路径
    """
    return get_client().generate_character_image(character_name, description, source, save_dir)
