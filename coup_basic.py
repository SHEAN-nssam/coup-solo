from enum import Enum
import random
from random import shuffle
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time


class Role(Enum):
    """角色枚举，用于类型保护"""
    DUKE = "duke"
    ASSASSIN = "assassin"
    CAPTAIN = "captain"
    AMBASSADOR = "ambassador"
    CONTESSA = "contessa"


class ActionType(Enum):
    """行动类型枚举"""
    INCOME = "income"
    FOREIGN_AID = "foreign_aid"
    COUP = "coup"
    TAX = "tax"
    ASSASSINATE = "assassinate"
    STEAL = "steal"
    EXCHANGE = "exchange"


@dataclass
class ActionMetadata:
    """行动的元数据配置"""
    name_cn: str
    requires_target: bool
    required_role: Optional[Role]  # 宣称所需角色（None表示无需宣称）
    counterable_by: List[Role]  # 可阻挡的角色列表
    coins_cost: int = 0  # 新增：金币消耗（默认0）


# ==================== 核心配置表 ====================
# 使用枚举作为键，IDE会检查拼写错误
ACTION_CONFIG = {
    ActionType.INCOME: ActionMetadata(
        name_cn="收入",
        requires_target=False,
        required_role=None,
        counterable_by=[],
        coins_cost=0
    ),
    ActionType.FOREIGN_AID: ActionMetadata(
        name_cn="外援",
        requires_target=False,
        required_role=None,
        counterable_by=[Role.DUKE],
        coins_cost=0
    ),
    ActionType.COUP: ActionMetadata(
        name_cn="政变",
        requires_target=True,
        required_role=None,
        counterable_by=[],
        coins_cost=7  # 政变消耗7金币
    ),
    ActionType.TAX: ActionMetadata(
        name_cn="税收",
        requires_target=False,
        required_role=Role.DUKE,
        counterable_by=[],
        coins_cost=0
    ),
    ActionType.ASSASSINATE: ActionMetadata(
        name_cn="暗杀",
        requires_target=True,
        required_role=Role.ASSASSIN,
        counterable_by=[Role.CONTESSA],
        coins_cost=3  # 暗杀消耗3金币
    ),
    ActionType.STEAL: ActionMetadata(
        name_cn="偷窃",
        requires_target=True,
        required_role=Role.CAPTAIN,
        counterable_by=[Role.CAPTAIN, Role.AMBASSADOR],
        coins_cost=0
    ),
    ActionType.EXCHANGE: ActionMetadata(
        name_cn="交换",
        requires_target=False,
        required_role=Role.AMBASSADOR,
        counterable_by=[],
        coins_cost=0
    )
}




# 定义行动处理器接口

class ActionHandler(ABC):
    """抽象行动处理器"""

    @abstractmethod
    def execute(self, gm: 'GameManager', actor: 'Player', choice: Dict[str, Any]) -> bool:
        """
        执行具体行动效果
        返回: 是否成功执行
        """
        pass


# ==================== 2. 为每个行动创建处理器 ====================

class IncomeHandler(ActionHandler):
    """收入处理器"""

    def execute(self, gm: 'GameManager', actor: 'Player', choice: Dict) -> bool:
        actor.get_coin(1)
        print(f"{actor.name}执行收入，获得1金币")
        return True


class ForeignAidHandler(ActionHandler):
    """外援处理器"""

    def execute(self, gm: 'GameManager', actor: 'Player', choice: Dict) -> bool:
        actor.get_coin(2)
        print(f"{actor.name}执行外援，获得2金币")
        return True


class TaxHandler(ActionHandler):
    """税收处理器"""

    def execute(self, gm: 'GameManager', actor: 'Player', choice: Dict) -> bool:
        actor.get_coin(3)
        print(f"{actor.name}执行税收，获得3金币")
        return True


class StealHandler(ActionHandler):
    """偷窃处理器"""

    def execute(self, gm: 'GameManager', actor: 'Player', choice: Dict) -> bool:
        target = gm.get_player_by_id(choice["target_id"])
        if not target:
            return False

        stolen = min(2, target.coins)
        target.lose_coin(stolen)
        actor.get_coin(stolen)
        print(f"{actor.name}从{target.name}偷窃了{stolen}金币")
        return True


class AssassinateHandler(ActionHandler):
    """暗杀处理器"""

    def execute(self, gm: 'GameManager', actor: 'Player', choice: Dict) -> bool:
        target: Player = gm.get_player_by_id(choice["target_id"])
        print(target)
        if not target:
            return False

        print(f"{actor.name}暗杀{target.name}成功")
        target.lose_influence()  # 目标失去1影响力
        # gm._check_player_death(target)
        return True


class CoupHandler(ActionHandler):
    """政变处理器"""

    def execute(self, gm: 'GameManager', actor: 'Player', choice: Dict) -> bool:
        target = gm.get_player_by_id(choice["target_id"])
        if not target:
            return False

        print(f"{actor.name}发动政变，目标{target.name}失去1影响力")
        target.lose_influence()  # 强制翻开一张牌
        # gm._check_player_death(target)
        return True


class ExchangeHandler(ActionHandler):
    """交换处理器"""

    def execute(self, gm: 'GameManager', actor: 'Player', choice: Dict) -> bool:
        gm.exchange_two_cards(actor)  # 复用已有方法
        print(f"{actor.name}完成交换")
        return True


class Deck:
    """
    牌堆类，用于初始化牌堆，抽牌和接受返回的牌。由抽牌和接受返回的牌构成大使的换牌操作
    """

    def __init__(self, i=0):
        self._cards: List[Role] = [role for role in Role for _ in range(3 + i)]
        shuffle(self._cards)

    def draw(self, num: int = 1) -> List[Role]:
        """从牌堆顶抽牌"""
        if num > len(self._cards):
            # 牌堆不够时，报错
            raise ValueError(f"牌堆只剩{len(self._cards)}张，无法抽取{num}张！")

        drawn = [self._cards.pop() for _ in range(num)]
        return drawn

    def return_cards(self, cards: List[Role]):
        """将牌直接返回牌堆（而非弃牌堆）"""
        self._cards.extend(cards)  # 直接加回牌堆
        shuffle(self._cards)  # 保持随机性

    def remaining(self) -> int:
        """返回牌堆剩余牌数（始终等于总牌数）"""
        return len(self._cards)

    def __str__(self):
        return f"牌堆: {len(self._cards)}张\n牌堆全部内容:{self._cards}"


@dataclass
class Influence:
    """单张影响力牌：角色 + 翻开状态"""
    role: Role
    is_revealed: bool = False  # 默认暗置

    @property
    def is_reveal(self):
        return self.is_revealed

    def reveal(self):
        self.is_revealed = True
        return


# 古典风格英文译中文名字池（男女混合，30个）
CLASSICAL_NAMES_POOL = [
    "奥菲莉亚 (Ophelia)", "塞巴斯蒂安 (Sebastian)", "伊莎贝拉 (Isabella)", "埃德蒙 (Edmund)",
    "阿拉贝拉 (Arabella)", "塞西尔 (Cecil)", "约瑟芬 (Josephine)", "奥古斯都 (Augustus)",
    "卡珊德拉 (Cassandra)", "本尼迪克特 (Benedict)", "佩内洛普 (Penelope)", "马库斯 (Marcus)",
    "塞勒涅 (Selene)", "卢修斯 (Lucius)", "瓦伦蒂娜 (Valentina)", "德米特里 (Demetrius)",
    "伊莲娜 (Elena)", "费边 (Fabian)", "莉维亚 (Livia)", "卡西乌斯 (Cassius)",
    "阿塔兰塔 (Atalanta)", "塞弗勒斯 (Severus)", "弗洛拉 (Flora)", "马格努斯 (Magnus)",
    "海伦娜 (Helena)", "珀西瓦尔 (Percival)", "维多利亚 (Victoria)", "卢卡斯 (Lucas)",
    "卡米拉 (Camilla)", "康拉德 (Conrad)"
]


class Player:

    def __init__(self, player_name: str, player_id: int, cards: List[Role]):
        self.name = player_name
        self.player_id = player_id
        # 核心状态
        self.coins: int = 2  # 起始 2 金币
        cards = cards[:2]
        self.influence: List[Influence] = [Influence(c) for c in cards]  # 现在是Influence对象列表
        self.alive: bool = True

        # 行动记录（用于AI学习和游戏回放）
        self.action_history: List[Dict[str, Any]] = []

    # ===== 核心方法：状态查询 =====
    def display(self):
        """面向其他玩家展示自身信息，不暴露具体牌组，待改"""
        # 编写一个简单的语句，使得牌组中有几张没翻开的牌就显示数字几
        count = sum(1 for i in self.influence if not i.is_revealed)
        print(f"{self.player_id}号玩家:{self.name}  金币数:{self.coins} 当前影响力:{count}")
        return

    @property
    def is_alive(self):
        """通过检查所有牌是否都被翻开判断存活"""
        self.alive = not all(i.is_reveal for i in self.influence)
        # print(any(i.is_reveal for i in self.influence))
        return not all(i.is_reveal for i in self.influence)

    @property
    def hidden_cards(self) -> List[Role]:
        """获取所有未翻开的角色（暗牌），用于换牌"""
        return [inf.role for inf in self.influence if not inf.is_revealed]

    def get_hidden_cards(self) -> List[Influence]:
        """获取所有未翻开的影响力牌"""
        return [i for i in self.influence if not i.is_reveal]

    @property
    def revealed_cards(self) -> List[Role]:
        """获取所有已翻开的角色（明牌），仅用于UI显示"""
        return [inf.role for inf in self.influence if inf.is_revealed]

    def has_role(self, role: Role) -> bool:
        """检查是否拥有某角色（无论是否翻开）"""
        return any(inf.role == role for inf in self.influence)

    def has_hidden_role(self, role: Role) -> bool:
        """检查是否拥有某暗牌（用于AI欺骗逻辑），用于质疑判断"""
        return any(inf.role == role and not inf.is_revealed for inf in self.influence)

    # ===== 核心方法：状态修改 =====
    def get_coin(self, n: int):
        self.coins = self.coins + n
        return

    def lose_coin(self, n: int):
        self.coins = self.coins - n
        return

    def add_influence(self, cards: List[Role]):
        """添加新牌（初始发牌或交换）"""
        self.influence.extend([Influence(role=card) for card in cards])
        self._log_action("add_influence", {"cards": [c.value for c in cards]})

    def lose_influence(self):
        """失去影响力（选择牌翻开）"""

        if not self.is_alive:
            print(f"{self.player_id}号玩家失去所有影响力")
        return

    def challenge_or_not(self, pl: 'Player', ro: Role):
        """选择对于其他玩家的某宣言行动是否进行质疑
        形参需要宣言玩家和所宣言身份
        """
        return

    def deal_challenge(self):
        """返回True为揭牌->质疑失败，False为不揭牌->质疑成功"""
        return

    def get_available_actions(self):
        """根据玩家状态生成可选行动"""
        # 基础行动（永远可用）
        actions = [ActionType.INCOME, ActionType.STEAL, ActionType.TAX,
                   ActionType.EXCHANGE, ActionType.FOREIGN_AID]

        # 金币≥3才能暗杀
        if self.coins >= 3:
            actions.append(ActionType.ASSASSINATE)

        # 金币≥7才能政变
        if self.coins >= 7:
            actions.append(ActionType.COUP)

        if self.coins >= 10:
            actions = [ActionType.COUP]

        return actions

    def get_player_choice(self, target_list):
        """玩家接受行动菜单和目标列表，返回选择。
        在两个类中分别继承重写

        """
        # [{"player_id": int, "name": str, "coins": int, "hidden_cards": int}]
        actions = self.get_available_actions()
        return

    def target_answer(self, action: ActionType):
        """玩家自身作为被执行行动的目标，action是将要被执行的行动
        是否宣言自己持有对应行动的反制角色
        """

        return

    # ===== 工具方法 =====
    def _log_action(self, action_type: str, data: Dict[str, Any]):
        """记录行动日志"""
        self.action_history.append({
            "type": action_type,
            "data": data,
            "timestamp": len(self.action_history)
        })

    def __str__(self):
        hidden = len(self.hidden_cards)
        revealed = len(self.revealed_cards)
        status = "存活" if self.alive else "阵亡"
        # status = self.alive
        return (f"No.{self.player_id} Player: | "
                f"{self.name} | "
                f"💰{self.coins} | "
                f"{self.influence} | "
                f"🎭{hidden}暗/{revealed}明 | "
                f"{status}")

    def select_cards_to_keep(self, new_cards: List[Role],
                               hidden_cards: List[Role],
                               keep_count: int) :
        pass


class HumanPlayer(Player):
    def __init__(self, player_name: str, player_id: int, cards: List[Role]):
        # 调用父类初始化
        super().__init__(player_name, player_id, cards)
        '''
        # 自动打印人类玩家的角色信息
        role_names = [i.role.value for i in self.influence]  # 提取角色名
        print(f"\n🎮 人类玩家初始化: ID={self.player_id} | 名称={self.name}")
        print(f"   持有角色: {', '.join(role_names)}")
        '''

    def _display_hand_info(self):
        """辅助方法：显示完整手牌信息（明牌显示，暗牌隐藏）"""
        print("=" * 40)
        print(f"{self.name} 的手牌详情:")
        for idx, inf in enumerate(self.influence, 1):
            status = "【已翻开】" if inf.is_reveal else "【暗置】"
            print(f"  位置 {idx}: {inf.role.value} {status}")
        print("=" * 40)


    def get_player_choice(self, target_list):
        """玩家接受行动菜单和目标列表，返回选择。
        [{"player_id": int, "name": str, "coins": int, "hidden_cards": int}]
        """
        actions = self.get_available_actions()
        if not actions:
            raise ValueError("当前玩家没有可用行动")
            # 人类玩家：控制台交互
        print(f"\n--- {self.name} 的选择 ---")

        # 循环直到获得有效选择
        while True:
            print("\n--- 你的回合 ---")
            print("可选行动：")
            for idx, action in enumerate(actions, 1):
                meta = ACTION_CONFIG[action]
                print(f"{idx}. {meta.name_cn} ({action.value})")

            choice = input("选择行动编号: ").strip()

            if choice.isdigit() and 1 <= int(choice) <= len(actions):
                selected_action = actions[int(choice) - 1]

                # 检查是否需要目标
                target_id = None
                if ACTION_CONFIG[selected_action].requires_target:
                    if not target_list:
                        raise ValueError("该行动需要目标，但目标列表为空")

                    print("\n可选目标：")
                    for idx, target in enumerate(target_list, 1):
                        print(f"{idx}. 玩家{target['player_id']}({target['name']}) - 金币:{target['coins']}")

                    target_choice = input("选择目标编号: ").strip()
                    if target_choice.isdigit() and 1 <= int(target_choice) <= len(target_list):
                        target_id = target_list[int(target_choice) - 1]["player_id"]
                    else:
                        print("无效的目标选择，请重新输入")
                        continue  # 重新循环，不返回

                # 成功获得有效选择，返回字典
                return {
                    "action": selected_action,
                    "target_id": target_id
                }
            else:
                print("无效的行动选择，请重新输入")
                # 继续循环，不返回

    def challenge_or_not(self, pl: 'Player', ro: Role) -> bool:
        """选择对于其他玩家的某宣言行动是否进行质疑
        形参需要宣言玩家和所宣言身份
        """
        print(f"{pl.name} (ID:{pl.player_id}) 宣称使用【{ro.value}】的能力")
        while True:
            choice = input("要质疑吗？（1-是/0-否）")
            if choice.isdigit() and int(choice) in [0, 1]:
                choice = (choice == "1")
                break
            print("无效输入，请重新选择")
        return choice

    def lose_influence(self):
        # 如果有两张没翻开的牌才需要做选择
        # 只剩一张则直接翻开剩下的一张，并且宣布死亡
        """人类玩家：交互式选择翻开哪张牌"""
        hidden_cards = self.get_hidden_cards()

        # 如果没有可翻开的牌
        if not hidden_cards:
            print(f"{self.name}没有未翻开的影响力牌")
            return None

        # 如果只有一张，直接翻开
        if len(hidden_cards) == 1:
            card = hidden_cards[0]
            card.reveal()
            print(f"{self.name}翻开唯一的影响力牌：{card.role.value}")
            if not self.is_alive:
                print(f"{self.player_id}号玩家失去所有影响力")
            return card.role

        # 有两张，让玩家选择
        print(f"\n--- {self.name} 需要翻开一张影响力牌 ---")
        print("你的暗牌：")
        for idx, card in enumerate(hidden_cards, 1):
            print(f"  {idx}. {card.role.value}")

        # 循环直到获得有效输入
        while True:
            choice = input("请选择要翻开的牌 (1/2): ").strip()
            if choice in ["1", "2"]:
                selected_card = hidden_cards[int(choice) - 1]
                selected_card.reveal()
                print(f"{self.name}选择翻开：{selected_card.role.value}")
                return selected_card.role
            else:
                print("无效输入，请输入1或2")

    def deal_challenge(self):
        """返回True为揭牌->质疑失败，False为不揭牌->质疑成功"""
        print("你的当前手牌：")
        self._display_hand_info()
        while True:
            choice = input("你拥有应对质疑的角色，是否揭开以回应质疑？（1-是/0-否）")
            if choice.isdigit() and int(choice) in [0, 1]:
                choice = bool(choice)
                break
            print("无效输入，请重新选择")
        return choice

    def select_cards_to_keep(self, new_cards: List[Role],
                               hidden_cards: List[Role],
                               keep_count: int)  -> List[Role]:
        """
        人类玩家：从所有暗牌（原有暗牌+新抽牌）中选择保留的牌
        选择数量 = keep_count
        """
        all_cards = new_cards.copy() + hidden_cards.copy()
        selected = []
        remaining = all_cards.copy()
        print(f"\n🃏 {self.name} 的换牌选择")
        print(f"你必须保留 {keep_count} 张暗牌")

        print("\n原有暗牌：")
        for i, c in enumerate(hidden_cards, 1):
            print(f"  {i}. 【原有】{c.value}")

        print("\n新抽到的牌：")
        for i, c in enumerate(new_cards, 1):
            print(f"  {len(hidden_cards) + i}. 【新牌】{c.value}")

        print(f"\n总共 {len(all_cards)} 张暗牌，选择 {keep_count} 张保留")



        # 依次选择keep_count张牌
        for i in range(keep_count):
            print(f"\n--- 选择第{i + 1}张牌（剩余 {len(remaining)} 张可选）---")

            # ✅ 每次选牌前都重新显示剩余卡牌（统一编号）
            for idx, card in enumerate(remaining, 1):
                #card_type = "【新牌】" if card in new_cards else "【原有】"
                print(f"  {idx}.{card.value}")

            # 循环直到获得有效选择
            while True:
                try:
                    idx = int(input(f"选择编号 (1-{len(remaining)}): "))
                    if 1 <= idx <= len(remaining):
                        # ✅ 从remaining中移除并添加到selected
                        selected_card = remaining.pop(idx - 1)
                        selected.append(selected_card)

                        '''
                        # ✅ 从原始列表中也移除，保持同步
                        if selected_card in new_cards:
                            new_cards.remove(selected_card)
                        if selected_card in hidden_cards:
                            hidden_cards.remove(selected_card)
                        '''
                        break
                    else:
                        print("  编号超出范围")
                except ValueError:
                    print("  无效输入，请输入数字")


        print(f"你选择了: {[c.value for c in selected]}")
        return selected


    def target_answer(self, action: ActionType):
        """玩家自身作为被执行行动的目标，action是将要被执行的行动
        是否宣言自己持有对应行动的反制角色
        """
        # 查询可反制角色列表
        counter_roles = ACTION_CONFIG[action].counterable_by
        # 如果该行动不可反制，直接返回None
        if not counter_roles:
            return None

        # 生成选择列表：[可用角色..., None]
        options = counter_roles + [None]

        # 打印菜单供玩家选择
        print(f"\n--- {self.name} 被攻击！你可以选择反制 ---")
        print(f"攻击类型: {ACTION_CONFIG[action].name_cn}")
        print("你的反制选项：")

        for idx, option in enumerate(options, 1):
            if option is None:
                print(f"{idx}. 不反制")
            else:
                print(f"{idx}. 使用 {option.value} 反制")

        # 循环直到获得有效输入
        while True:
            choice = input("请选择 (输入编号): ").strip()

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    selected = options[idx]

                    if selected is None:
                        print(f"{self.name} 选择不反制")
                    else:
                        print(f"{self.name} 宣言使用 {selected.value} 反制！")

                    return selected
                else:
                    print(f"无效编号，请输入1-{len(options)}")
            else:
                print("无效输入，请输入数字")



class ComputerPlayer(Player):

    def get_player_choice(self, target_list):
        """玩家接受行动菜单和目标列表，返回选择。
        [{"player_id": int, "name": str, "coins": int, "hidden_cards": int}]
        """
        actions = self.get_available_actions()
        if not actions:
            raise ValueError("当前玩家没有可用行动")

        selected_action = random.choice(actions)
        time.sleep(random.uniform(1.0, 4.0))

        target_id = None
        if ACTION_CONFIG[selected_action].requires_target and target_list:
            # 随机选择目标（可扩展为更智能的AI）
            target = random.choice(target_list)
            target_id = target["player_id"]

        print(f"\n{self.name}(AI) 选择了 {selected_action.value}"
              f"{f' 目标: {target_id}' if target_id else ''}")

        return {
            "action": selected_action,
            "target_id": target_id
        }

    def challenge_or_not(self, pl: 'Player', ro: Role) -> bool:
        """选择对于其他玩家的某宣言行动是否进行质疑
        形参需要宣言玩家和所宣言身份
        """
        re = random.choice([True, False])
        time.sleep(random.uniform(1.0, 4.0))
        return re

    def lose_influence(self):
        hidden_cards = self.get_hidden_cards()

        # 如果没有可翻开的牌
        if not hidden_cards:
            print(f"{self.name}没有未翻开的影响力牌")
            return None

        # 如果只有一张，直接翻开
        if len(hidden_cards) == 1:
            card = hidden_cards[0]
            card.reveal()
            print(f"{self.name}翻开唯一的影响力牌：{card.role.value}")
            if not self.is_alive:
                print(f"{self.player_id}号玩家失去所有影响力")
            return card.role
        time.sleep(random.uniform(1.0, 4.0))
        # 随机选择
        # 使用random.random()模拟random.choice
        selected_card = hidden_cards[int(random.random() * len(hidden_cards))]
        selected_card.reveal()
        print(f"{self.name}(AI)随机翻开：{selected_card.role.value}")
        return selected_card.role

    def deal_challenge(self):
        """返回True为揭牌->质疑失败，False为不揭牌->质疑成功"""
        time.sleep(random.uniform(1.0, 4.0))
        re = random.choice([True, False])
        return re

    def select_cards_to_keep(self, new_cards: List[Role],
                               hidden_cards: List[Role],
                               keep_count: int) -> List[Role]:
        """
        CPU玩家：基于权重从所有暗牌中选择保留的牌
        """
        all_cards = new_cards + hidden_cards
        time.sleep(random.uniform(1.0, 4.0))
        # 按权重排序，取前keep_count个
        weights = {Role.DUKE: 5, Role.ASSASSIN: 4, Role.CAPTAIN: 3, Role.AMBASSADOR: 2, Role.CONTESSA: 1}
        sorted_cards = sorted(all_cards, key=lambda c: weights[c], reverse=True)
        selected = sorted_cards[:keep_count]

        print(f"{self.name}(AI) 选择保留: {[c.value for c in selected]}")
        return selected


    def target_answer(self, action: ActionType):
        """玩家自身作为被执行行动的目标，action是将要被执行的行动
        是否宣言自己持有对应行动的反制角色
        """
        # 查询可反制角色列表
        counter_roles = ACTION_CONFIG[action].counterable_by
        # 如果该行动不可反制，直接返回None
        if not counter_roles:
            return None

        # 生成选择列表：[可用角色..., None]
        options = counter_roles + [None]

        # 4. 如果只有None选项，直接返回
        if len(options) == 1:
            return None

        # 5. CPU随机选择（使用random()模拟random.choice）
        # 简单AI：60%概率选择最强反制角色，40%概率不反制
        if random.random() < 0.6 and counter_roles:
            # 选择权重最高的反制角色
            role_weights = {Role.DUKE: 5, Role.ASSASSIN: 4, Role.CAPTAIN: 3, Role.AMBASSADOR: 2, Role.CONTESSA: 1}
            selected = max(counter_roles, key=lambda r: role_weights[r])
        else:
            selected = None

        # 6. 记录决策
        if selected:
            print(f"{self.name}(AI) 宣言使用 {selected.value} 反制！")
        else:
            print(f"{self.name}(AI) 选择不反制")
        time.sleep(random.uniform(1.0, 4.0))
        return selected


# GameState类，只负责快照保存和决策记录？

# 传入一共需要几个玩家，有几个是人类玩家，自动生成对应的混合了人类玩家和电脑玩家的玩家数组，交给电脑进行处理
class GameManager:
    def __init__(self, pls: int = 3, hpls: int = 1):
        # 玩家怎么配置，场外？
        # self.players: List[Player] = players
        # 场外传要场外生成，还是只传人数吧
        self.total_player_num = pls
        self.human_player_num = hpls
        self.i = 0
        while self.total_player_num * 2 >= (3 + self.i) * 5:
            self.i = self.i + 2
        self.deck = Deck(self.i)
        self.players = []

        self.names_pool = CLASSICAL_NAMES_POOL.copy()
        self.initialize_players()
        human_player = None
        for player in self.players:
            if isinstance(player, HumanPlayer):
                human_player = player
        print(human_player)
        self.current_player_index = 0  # 记录当前轮到谁
        self.current_player = self.players[0]
        self.turn_count = 1  # 回合计数器

        # 处理器映射字典
        self._action_handlers: Dict[ActionType, ActionHandler] = {
            ActionType.INCOME: IncomeHandler(),
            ActionType.FOREIGN_AID: ForeignAidHandler(),
            ActionType.TAX: TaxHandler(),
            ActionType.STEAL: StealHandler(),
            ActionType.ASSASSINATE: AssassinateHandler(),
            ActionType.COUP: CoupHandler(),
            ActionType.EXCHANGE: ExchangeHandler(),
        }

    def initialize_players(self) -> List[Player]:
        # 只输入玩家人数由管理器自动生成对应数量玩家的设置
        if not (3 <= self.total_player_num <= 10):
            raise ValueError("总玩家数应在3到10之间")
        if not (1 <= self.human_player_num <= self.total_player_num):
            raise ValueError("人类玩家数不能大于总玩家数或小于1")

        # 清空玩家列表
        self.players = []

        for idx in range(self.human_player_num):
            initial_cards = self.deck.draw(2)
            name = "Hum"
            # 名字选择逻辑
            while True:
                print(f"\n🎮 创建人类玩家 {idx + 1}/{self.human_player_num}:")
                print("1. 自己输入名字")
                print("2. 从名字池随机选择")
                choice = input("请选择 (1或2): ").strip()

                if choice == "1":
                    name = input("请输入名字: ").strip()
                    if name:
                        break
                    print("名字不能为空")
                elif choice == "2":
                    if not self.names_pool:
                        print("⚠️  名字池已空，请自己输入名字")
                        continue
                    name = random.choice(self.names_pool)
                    self.names_pool.remove(name)
                    print(f"随机分配名字: {name}")
                    break
                else:
                    print("无效输入，请输入1或2")

            player = HumanPlayer(
                # player_name=f"Hum_{idx + 1}",
                player_name=name,
                player_id=idx,
                cards=initial_cards
            )
            self.players.append(player)

        for idx in range(self.total_player_num - self.human_player_num):
            initial_cards = self.deck.draw(2)

            # CPU从名字池随机选择
            if self.names_pool:
                cpu_name = random.choice(self.names_pool)
                self.names_pool.remove(cpu_name)
            else:
                cpu_name = f"CPU_{idx + 1}"  # 名字池空时的备用方案

            player = ComputerPlayer(
                #player_name=f"CPU_{idx + 1}",
                player_name=cpu_name,
                player_id=idx,
                cards=initial_cards
            )
            self.players.append(player)

        # 洗牌玩家顺序（交错排列）
        shuffle(self.players)

        # 重新分配ID保证连续
        for idx, player in enumerate(self.players):
            player.player_id = idx

        # 打印创建结果
        print(f"\n=== 玩家创建完成===")
        for p in self.players:
            type_str = "人类" if isinstance(p, HumanPlayer) else "电脑"
            print(f"玩家 {p.player_id}: ({type_str}) - 手牌: {len(p.influence)}张")
        print()
        return self.players

    def get_player_by_id(self, pid: int) -> Player:
        if not (0 <= pid <self.total_player_num):
            raise IndexError("id号超出范围")
        p = next((p for p in self.players if p.player_id == pid),
                 None  # 默认值，找不到时返回
                 )
        return p

    def get_current_player(self) -> Optional[Player]:
        """
        用于回合轮转的计数，调整current_player_index的数值，使得不同玩家分别掌管回合
        :return:
        """
        t_index: int = (self.current_player_index + 1) % self.total_player_num
        # print(f"t_index:{t_index}")
        # print(self.players[t_index])
        while not self.players[t_index].is_alive:
            t_index: int = (t_index + 1) % self.total_player_num
        self.current_player_index = t_index
        return self.players[t_index]

    def exchange_single_card(self, player: Player, role_to_return: Role) -> bool:
        """
        将一张特定角色的未翻开牌放回牌堆，再随机抽一张加入手牌
        返回：是否成功
        """
        # 1. 验证玩家有未翻开的牌
        hidden_cards = player.get_hidden_cards()
        if not hidden_cards:
            print(f"{player.name}没有未翻开的牌，无法换牌")
            return False

        # 2. 验证玩家有这张特定角色的未翻开牌
        target_card = next((card for card in hidden_cards if card.role == role_to_return), None)
        if not target_card:
            print(f"{player.name}没有未翻开的{role_to_return.value}牌")
            return False

        # 3. 移除这张牌并放回牌堆
        player.influence.remove(target_card)
        self.deck.return_cards([role_to_return])
        print(f"{player.name}放回了一张{role_to_return.value}牌")

        # 4. 从牌堆抽一张新牌
        new_card = self.deck.draw(1)[0]
        player.influence.append(Influence(new_card))
        print(f"{player.name}抽到了一张{new_card.value}牌")

        return True

    def exchange_two_cards(self, player: Player) -> bool:
        """
        大使换牌：从牌堆抽2张牌，玩家从所有暗牌（原有+新抽）中选择保留数量张

        流程：
        1. 获取玩家当前暗牌数量（keep_count）
        2. 从牌堆抽2张新牌
        3. 调用玩家方法，从所有暗牌（原有+新抽）中选择keep_count张保留
        4. 计算未选择的2张牌并放回牌堆
        """
        # 1. 获取玩家暗牌和保留数量
        hidden_cards = player.get_hidden_cards()  # 原有暗牌
        keep_count = len(hidden_cards)  # 必须保留这么多张

        if keep_count == 0:
            raise ValueError(f"{player.name}没有暗牌，无法使用大使能力")

        # 2. 从牌堆抽2张新牌
        new_cards = self.deck.draw(2)
        print(f"\n🃏 牌堆提供的新牌: {[c.value for c in new_cards]}")

        # 3. 调用玩家方法进行选择（多态调用）
        # 传递：新牌列表、原有暗牌角色列表、保留数量
        selected = player.select_cards_to_keep(
            new_cards=new_cards,
            hidden_cards=[inf.role for inf in hidden_cards],
            keep_count=keep_count
        )

        # 4. 验证选择数量正确
        if len(selected) != keep_count:
            raise ValueError(f"玩家必须选择{keep_count}张牌，但只选择了{len(selected)}张")

        # 5. 执行换牌逻辑
        # 5.1 移除所有原有暗牌
        for card in hidden_cards:
            player.influence.remove(card)

        # 5.2 添加选中的牌（暗置）
        player.influence.extend(Influence(c) for c in selected)

        # 5.3 计算并返回未选择的牌（一定是2张）
        all_cards = new_cards + [inf.role for inf in hidden_cards]
        return_cards = [c for c in all_cards if c not in selected]

        # 5.4 将未选择的牌放回牌堆
        if return_cards:
            self.deck.return_cards(return_cards)
            print(f"🔄 放回牌堆: {[c.value for c in return_cards]}")

        print(f"✅ 换牌完成！{player.name}现在有 {keep_count} 张暗牌")
        return True


    def deal_challenge(self, pl1: Player, pl2: Player, role: Role):
        # pl1为被质疑者，pl2为质疑者
        result = False
        if not pl1.has_hidden_role(role):
            # 如果被质疑者没有该角色
            # 扣除被质疑者（pl1）的影响力
            time.sleep(random.uniform(1.0, 4.0))
            pl1.lose_influence()
            result = True
        else:
            if pl1.deal_challenge():
                # pl1换牌
                self.exchange_single_card(pl1, role)
                pl2.lose_influence()
                result = False
            else:
                time.sleep(random.uniform(1.0, 4.0))
                pl1.lose_influence()
                result = True
        return result

    def process_action_cost(self, player: Player, action: ActionType) -> tuple[bool, int]:
        """
        处理行动的金币消耗（独立方法，便于区分返还逻辑）
        参数:
            player: 执行行动的玩家
            action: 行动类型
        返回:
            tuple[bool, int]: (是否成功处理, 消耗的金币数)
            - 成功但消耗0金币: (True, 0)
            - 成功消耗N金币: (True, N)
        抛出:
            ValueError: 金币不足时抛出
        """
        # 从配置表获取行动消耗（默认为0）
        cost = ACTION_CONFIG[action].coins_cost

        # 如果消耗为0，直接返回成功
        if cost == 0:
            return True, 0

        # 验证金币是否充足
        if player.coins < cost:
            raise ValueError(
                f"{player.name}金币不足：需要{cost}，当前只有{player.coins}"
            )

        # 扣除金币（调用玩家的lose_coin方法）
        player.lose_coin(cost)
        print(f"{player.name}消耗了{cost}金币执行{action.value}")

        # 返回成功标志和消耗金额（用于后续返还判断）
        return True, cost

    def display_all_players(self):
        for p in self.players:
            Player.display(p)
            # print(p)
        return

    @property
    def alive_players(self) -> List[Player]:
        """获取所有存活玩家"""
        # for p in self.players: print(f"{p.is_alive}")
        return [p for p in self.players if p.is_alive]

    def is_game_over(self) -> bool:
        """游戏结束条件：只剩1人存活"""
        # print(f"存活玩家数:{len(self.alive_players)}")
        return len(self.alive_players) <= 1

    def get_target_list(self):
        """跳过当回合玩家，将其他玩家的金币数，暗牌数作为参考，生成对应类型的数据
        返回格式：[{"player_id": int, "name": str, "coins": int, "hidden_cards": int}]
        """
        target_list = []
        for p in self.players:
            if p is self.current_player:
                # print("当回合玩家应从目标列表中剔除")
                continue
            if p.is_alive:
                # 将玩家编号，名字，金币数，暗牌数，加入列表，成为备选
                # 计算暗牌数量（未翻开的牌）
                hidden_count = sum(1 for i in p.influence if not i.is_reveal)
                target_list.append({
                    "player_id": p.player_id,
                    "name": p.name,
                    "coins": p.coins,
                    "hidden_cards": hidden_count
                })
        return target_list

    def execute_action(self, actor: Player, choice: Dict[str, Any]) -> bool:
        """
        执行行动（极度精简！所有具体逻辑委托给处理器）
        """
        action = choice["action"]

        # 获取对应处理器
        handler = self._action_handlers.get(action)
        if not handler:
            raise ValueError(f"未找到行动处理器: {action}")

        # 委托执行
        return handler.execute(self, actor, choice)

    def run_game(self):
        # print(self.is_game_over())
        self.current_player = self.players[0]
        while not self.is_game_over():
            # 面向人类玩家，展示所有玩家的存活情况和经济情况
            # self.current_player = self.players[self.current_player_index]
            print("="*40)
            print(f"第{self.turn_count}回合-当前玩家:{self.current_player.name}")
            self.display_all_players()
            tl = self.get_target_list()
            # print(f"tl:{tl}")
            # get_player_choice
            # 玩家选择（根据人类玩家和CPU玩家进行不同处理），输入行动列表，输出玩家选择的具体行动
            choice = self.current_player.get_player_choice(tl)
            if choice is None:
                raise ValueError("玩家选择不能为空")
            print(f"玩家{self.current_player.name}选择进行{choice['action']}"
                  + (f"，行动目标为{choice['target_id']}号玩家" if choice['target_id'] is not None else ""))
            # choice格式 {"action": selected_action,"target_id": target_id}
            # if选择的行动有所属角色的宣称
            if ACTION_CONFIG[choice["action"]].required_role:
                challenger = None
                # 此处询问顺序需要修改
                for offset in range(1, self.total_player_num + 1):
                    # 计算目标索引，使用模运算实现循环
                    idx = (self.current_player_index + offset) % self.total_player_num
                    p = self.players[idx]

                    if p is self.current_player:
                        continue
                    elif not p.is_alive:
                        continue
                    else:
                        # action_challenge
                        # 依次询问其他玩家是否选择质疑，返回bool。
                        # 质疑具有唯一性，按序询问，但仅有一人可以质疑
                        if p.challenge_or_not(
                                self.current_player,
                                ACTION_CONFIG[choice["action"]].required_role):
                            challenger = p
                            break
                print(f"质疑者：{challenger}")
                if challenger:
                    # 处理质疑结果，输入质疑者，被质疑者，质疑角色，输出质疑成功或失败
                    # （同时在该函数内自动完成质疑失败的换牌）
                    result = self.deal_challenge(
                        self.current_player, challenger,
                        ACTION_CONFIG[choice["action"]].required_role)
                    # 如果质疑成功则会直接跳至下回合(先索引轮转再continue)
                    if result:
                        self.current_player = self.get_current_player()
                        self.turn_count = self.turn_count + 1
                        continue

            # 到这步该回合玩家没有被质疑，则行动的花销被正常支付（如刺杀的3个金币）
            # 好像只有刺杀花金币还会被反制
            self.process_action_cost(self.current_player, choice["action"])


            # if选择的行动有目标对象 and 存在对目标的反制角色
            if choice["target_id"] and ACTION_CONFIG[choice["action"]].counterable_by:
                '''
                target_player: Player = next(
                    (p for p in self.players if p.player_id == choice["target_id"]),
                    None ) # 默认值，找不到时返回
                '''
                target_player = self.get_player_by_id(choice["target_id"])
                print(target_player)
                target_choice = target_player.target_answer(choice["action"])
                # 询问目标玩家是否宣称有反制角色（如果有多个反制角色要宣称使用具体某一个）
                # 该方法返回None(即不反制)或宣称使用的反制角色(Role)

                if target_choice:
                    co_challenger = None
                    # 此处询问顺序需要修改
                    for offset in range(1, self.total_player_num + 1):
                        # 计算目标索引，使用模运算实现循环
                        idx = (target_player.player_id + offset) % self.total_player_num
                        p = self.players[idx]

                        if p is target_player:
                            continue
                        elif not p.is_alive:
                            continue
                        else:
                            # action_challenge
                            # 依次询问其他玩家是否选择质疑，返回bool。
                            # 质疑具有唯一性，按序询问，但仅有一人可以质疑
                            if p.challenge_or_not(
                                    target_player,
                                    target_choice):
                                co_challenger: Player = p
                                break

                    if co_challenger:
                        # 处理质疑结果，输入质疑者，被质疑者，质疑角色，输出质疑成功或失败
                        print(f"质疑者：{co_challenger}")
                        result = self.deal_challenge(
                            self.current_player, co_challenger,
                            target_choice)
                        # 如果质疑失败，即反制成功，行动将不被执行
                        if not result:
                            self.current_player = self.get_current_player()
                            self.turn_count = self.turn_count + 1
                            continue

                    else:  # 即无人质疑，该反制正常进行，直接跳至下回合
                        self.current_player = self.get_current_player()
                        self.turn_count = self.turn_count + 1
                        continue

                # 公爵对外援的反制还没做（无目标反制）
                elif ACTION_CONFIG[choice["action"]].counterable_by:
                    # 按顺序询问其他玩家是否宣言反制
                    counter_declared = False

                    for offset in range(1, self.total_player_num + 1):
                        idx = (self.current_player_index + offset) % self.total_player_num
                        potential_counter = self.players[idx]

                        if potential_counter is self.current_player:
                            continue
                        elif not potential_counter.is_alive:
                            continue
                        # 询问该玩家是否宣言反制
                        counter_choice = potential_counter.target_answer(choice["action"])

                        if counter_choice:
                            # 有玩家宣言反制，记录并停止询问
                            counter_declared = True
                            print(f"{potential_counter.name}宣言使用{counter_choice.value}反制！")

                            # 询问其他玩家是否质疑该反制
                            co_challenger = None
                            for offset2 in range(1, self.total_player_num + 1):
                                idx2 = (self.current_player_index + offset2) % self.total_player_num
                                p = self.players[idx2]

                                # 跳过反制玩家
                                if p is potential_counter:
                                    continue
                                elif not p.is_alive:
                                    continue

                                if p.challenge_or_not(potential_counter, counter_choice):
                                    co_challenger = p
                                    break

                            if co_challenger:
                                # 处理质疑
                                result = self.deal_challenge(
                                    potential_counter, co_challenger, counter_choice
                                )
                                # 如果质疑失败（反制有效），行动不执行
                                if not result:
                                    self.current_player = self.get_current_player()
                                    self.turn_count += 1
                                    continue
                                else:
                                    # 质疑成功（反制无效），继续执行行动
                                    pass
                            else:
                                # 无人质疑，反制有效，行动不执行
                                self.current_player = self.get_current_player()
                                self.turn_count += 1
                                continue

                            # 如果质疑成功则反制无效，继续执行行动
                            break  # 找到反制者后跳出循环

                # 如果质疑成功则反制无效，行动正常执行
            # 至此没有跳出，则行动有效，正常执行
            self.execute_action(self.current_player, choice)

            # 索引轮转
            self.current_player = self.get_current_player()
            self.turn_count = self.turn_count + 1
            # break
        winner = self.alive_players[0] if self.alive_players else None
        if winner:
            print(f"\n{'=' * 50}")
            print(f"🏆 游戏结束！获胜者: {winner.name} (ID:{winner.player_id})")
            print(f"{'=' * 50}")
        else:
            print("\n游戏异常结束：没有存活玩家")
        return


if __name__ == '__main__':
    gm = GameManager(4, 1)
    gm.run_game()


    '''
    print(gm.deck)
    human_player = None
    for player in gm.players:
        if isinstance(player, HumanPlayer):
            human_player = player
    # 模拟玩家手牌：大使（暗）+ 刺客（明）
    human_player.influence = [
        Influence(Role.AMBASSADOR, False),
        Influence(Role.ASSASSIN, False)
    ]

    print(f"换牌前: {[f'{c.role.value}({c.is_reveal})' for c in human_player.influence]}")

    # 执行交换
    try:
        gm.exchange_two_cards(human_player)
    except ValueError as e:
        print(e)
    print(f"换牌后: {[f'{c.role.value}({c.is_reveal})' for c in human_player.influence]}")
    print(f"牌堆剩余: {gm.deck.remaining()}张")
    '''
