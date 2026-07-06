import os
import random
import time
import logging

from .base import BaseTask
from ..paths import resource_path

logger = logging.getLogger("automation.nurture")

# 识图模板（养号流程用，与验证过的老程序一致）
ICON_DIR = resource_path("icon")
TIKTOK_ICON = os.path.join(ICON_DIR, "tiktok.bmp")   # 桌面 TikTok 图标
HOME_ICON = os.path.join(ICON_DIR, "home.png")       # TikTok 底部 Home
HEART_ICON = os.path.join(ICON_DIR, "heart.png")     # 视频右侧爱心

# 验证过的固定坐标（识图失败时兜底；来自实战养号程序）
FALLBACK_HOME = (41, 830)      # 底部 Home
FALLBACK_HEART = (386, 469)    # 点赞爱心
LANDSCAPE_FIX = (71, 387)      # 横屏(直播)时点这里切竖屏
LIVE_DOUBLE = (200, 500)       # 直播模式双击点赞位置
TIKTOK_SCHEME = "tiktok://"    # 打开 TikTok 的 URL scheme

DEFAULT_NURTURE_CONFIG = {
    # ── 总体控制 ──
    "total_duration_min": 30,        # 养号总时长（分钟），0=无限循环直到手动停止
    "session_count": 0,              # 总共刷多少轮（0=按时间控制）

    # ── 简单模式（强烈推荐）──
    # True 时只做最安全的动作：看视频 + 上滑 + 偶尔点赞，
    # 关闭所有会切页面的操作（搜索/切tab/评论/看主页/关注），避免跑到 Shop 等错误页面。
    "simple_mode": True,

    # ── 状态守卫（防止跑飞误入相册/其他App/购物页）──
    "guard_enabled": True,           # 是否启用状态守卫
    "guard_every_videos": 5,         # 每刷N个视频强制回一次推荐页
    "guard_similarity": 0.7,         # 桌面TikTok图标识别相似度

    # ── 刷视频参数 ──
    "videos_per_session": 15,        # 每轮刷多少个视频
    "watch_time_min": 3,             # 最短观看时间（秒）
    "watch_time_max": 30,            # 最长观看时间（秒）
    "long_watch_chance": 0.2,        # 长时间观看的概率（>15秒）
    "long_watch_time_min": 15,       # 长时间观看最短（秒）
    "long_watch_time_max": 60,       # 长时间观看最长（秒）
    "full_watch_chance": 0.1,        # 完整看完+重播的概率

    # ── 互动概率 ──
    "like_chance": 0.8,              # 点赞概率（实战养号流程默认几乎每个都点）
    "double_tap_like_chance": 0.60,  # 双击点赞 vs 按钮点赞的比例
    "follow_chance": 0.03,           # 关注概率
    "comment_chance": 0.0,           # 评论概率（初始为0，新号不建议评论）
    "share_chance": 0.0,             # 分享概率
    "profile_view_chance": 0.05,     # 查看发布者主页概率

    # ── 搜索行为 ──
    "search_enabled": True,          # 是否穿插搜索
    "search_interval_videos": 20,    # 每刷N个视频搜索一次
    "search_keywords": [],           # 搜索关键词列表（为空则跳过搜索）
    "search_browse_count": 3,        # 搜索后浏览几个结果

    # ── 休息 ──
    "rest_enabled": True,            # 是否穿插休息
    "rest_interval_videos": 30,      # 每刷N个视频休息一次
    "rest_time_min": 10,             # 休息最短时间（秒）
    "rest_time_max": 30,             # 休息最长时间（秒）

    # ── 其他行为 ──
    "switch_tab_chance": 0.03,       # 切换到发现/收件箱tab的概率
    "scroll_comments_chance": 0.05,  # 打开评论区浏览的概率

    # ── 操作间隔 ──
    "swipe_interval_min": 0.5,       # 滑动后最短等待（秒）
    "swipe_interval_max": 1.5,       # 滑动后最长等待（秒）
    "action_interval_min": 0.3,      # 操作间最短等待（秒）
    "action_interval_max": 1.0,      # 操作间最长等待（秒）
}


class NurtureTask(BaseTask):
    """TikTok 自动养号任务

    模拟真实用户刷视频行为:
    1. 打开 TikTok 进入推荐页
    2. 随机时长观看视频
    3. 随机概率点赞/关注/查看主页
    4. 穿插搜索行为
    5. 穿插休息

    所有时间和概率均可配置。
    """

    name = "nurture"
    description = "自动养号 - 模拟真人刷视频"

    def __init__(self, config=None):
        merged = dict(DEFAULT_NURTURE_CONFIG)
        if config:
            merged.update(config)
        super().__init__(merged)
        self._videos_watched = 0
        self._likes_given = 0
        self._follows_given = 0
        self._searches_done = 0
        self._sessions_done = 0
        self._live_mode = False   # 是否处于直播(横屏)模式

    def run(self, device):
        cfg = self.config
        total_duration = cfg["total_duration_min"] * 60
        session_limit = cfg["session_count"]
        # 轮次上限换算成视频上限（简单模式是连续刷，不分轮）
        video_limit = session_limit * cfg.get("videos_per_session", 15) if session_limit > 0 else 0
        simple = cfg.get("simple_mode", True)
        start_time = time.time()

        self._log(device, "开始养号流程" + ("（简单模式）" if simple else "（完整模式）"))
        self._update_progress()

        # 初始化：打开 TikTok 并进入 For You 推荐页（验证过的流程）
        self._init_device(device)

        if simple:
            # ── 简单模式：连续刷视频（忠实复刻实战养号流程）──
            while not self.should_stop:
                if total_duration > 0 and (time.time() - start_time) >= total_duration:
                    self._log(device, f"已达设定时长 {cfg['total_duration_min']} 分钟，结束")
                    break
                if video_limit > 0 and self._videos_watched >= video_limit:
                    self._log(device, f"已刷 {video_limit} 个视频，结束")
                    break
                self.check_pause()
                self._nurture_step(device)
                self._videos_watched += 1
                self._update_progress()
        else:
            # ── 完整模式：分轮 + 各种互动（未充分验证，opt-in）──
            session_idx = 0
            while not self.should_stop:
                if total_duration > 0 and (time.time() - start_time) >= total_duration:
                    break
                if session_limit > 0 and session_idx >= session_limit:
                    break
                session_idx += 1
                self._log(device, f"--- 第 {session_idx} 轮开始 ---")
                self._run_session(device)
                self._sessions_done = session_idx
                if not self.should_stop:
                    self.wait(random.uniform(5, 15))

        elapsed = (time.time() - start_time) / 60
        self._log(device, (
            f"养号结束 | 耗时: {elapsed:.1f}分钟 | "
            f"观看: {self._videos_watched} | 点赞: {self._likes_given}"
        ))

    # ═══════════════════════════════════════════
    # 简单模式：忠实复刻实战养号流程
    # ═══════════════════════════════════════════

    def _init_device(self, device):
        """初始化：回主屏 → 打开TikTok → 横屏检测 → 点Home → 右滑到For You"""
        cfg = self.config
        sim = cfg.get("guard_similarity", 0.7)

        # 1. 回主屏幕
        self._log(device, "回到主屏幕")
        device.press_home()
        self.wait(2)

        # 2. 打开 TikTok（用 tiktok:// scheme，验证过的方式）
        self._log(device, "打开 TikTok")
        device.open_url(TIKTOK_SCHEME)
        self.wait(5)

        # 3. 横屏检测 → 直播模式
        self._check_landscape(device)

        # 4. 点击底部 Home（识图优先，兜底固定坐标）
        loc = self._find_click(device, HOME_ICON, sim)
        if loc:
            self._log(device, f"识图Home ({loc[0]},{loc[1]})")
        else:
            device.tap(*FALLBACK_HOME)
            self._log(device, f"固定坐标Home {FALLBACK_HOME}")
        self.wait(2)

        # 5. 向右滑动切到 For You（滑3次）
        for _ in range(3):
            if self.should_stop:
                return
            device.swipe_dir("right", length=0.5, sx=100, sy=50)
            time.sleep(0.5)
        self.wait(2)
        self._log(device, "已进入 For You 推荐页")

    def _nurture_step(self, device):
        """刷一个视频：横屏检测 → 上滑 → 点赞（验证过的流程）"""
        cfg = self.config

        # 观看当前视频（随机停留，模拟观看；实战流程用 0-20 秒）
        watch = random.uniform(cfg.get("watch_time_min", 3), cfg.get("watch_time_max", 20))
        self._log(device, f"视频 {self._videos_watched + 1} - 观看 {watch:.0f}秒")
        self.wait(watch)
        if self.should_stop:
            return

        # 1. 横屏检测（刷到直播会横屏）
        self._check_landscape(device)

        # 2. 上滑到下一个视频
        device.swipe_dir("up", length=0.5, sx=200, sy=550)
        self.wait(1.5)
        if self.should_stop:
            return

        # 3. 点赞（按配置概率；实战流程默认每个都点）
        if random.random() < cfg.get("like_chance", 1.0):
            if self._live_mode:
                # 直播模式：双击屏幕中心
                device.tap(*LIVE_DOUBLE)
                time.sleep(0.15)
                device.tap(*LIVE_DOUBLE)
                self._log(device, "  双击点赞(直播)")
            else:
                loc = self._find_click(device, HEART_ICON, cfg.get("guard_similarity", 0.7))
                if loc:
                    self._log(device, f"  点赞 ({loc[0]},{loc[1]})")
                else:
                    device.tap(*FALLBACK_HEART)
                    self._log(device, f"  点赞 {FALLBACK_HEART}")
            self._likes_given += 1

    def _check_landscape(self, device):
        """检测横屏(直播)，是则点击切回竖屏并标记直播模式"""
        try:
            land = device.is_landscape()
            if land:
                device.tap(*LANDSCAPE_FIX)
                self.wait(1.5)
                self._live_mode = True
                self._log(device, "检测到横屏(直播)，已切换")
            elif land is False:
                self._live_mode = False
        except Exception:
            pass

    def _find_click(self, device, icon_path, sim):
        """识图找到并点击，返回坐标或 None"""
        if not os.path.exists(icon_path):
            return None
        loc = device.find_image_file(icon_path, sim)
        if loc:
            device.tap(loc[0], loc[1])
            time.sleep(0.5)
            return (loc[0], loc[1])
        return None

    # ── 核心流程 ──

    def _run_session(self, device):
        """一轮刷视频"""
        cfg = self.config
        target = cfg["videos_per_session"]

        for i in range(target):
            if self.should_stop:
                return
            self.check_pause()

            # 状态守卫（防止跑飞误入相册/其他App）：
            #  - 每个视频：轻量检测是否回到桌面（便宜，仅在跑飞时才动作）
            #  - 每隔N个视频：强制干净重进一次 TikTok（兜底任何卡死状态）
            if cfg.get("guard_enabled", True):
                force = (self._videos_watched > 0
                         and self._videos_watched % cfg.get("guard_every_videos", 6) == 0)
                self._ensure_tiktok(device, force=force)

            # 搜索穿插（简单模式下不搜索——搜索会切到顶部/Shop页，容易跑飞）
            if (not cfg.get("simple_mode", True)
                    and cfg["search_enabled"]
                    and cfg["search_keywords"]
                    and self._videos_watched > 0
                    and self._videos_watched % cfg["search_interval_videos"] == 0):
                self._do_search(device)

            # 休息穿插
            if (cfg["rest_enabled"]
                    and self._videos_watched > 0
                    and self._videos_watched % cfg["rest_interval_videos"] == 0):
                self._do_rest(device)

            # 刷一个视频
            self._watch_one_video(device, i + 1, target)
            self._videos_watched += 1
            self._update_progress()

    def _watch_one_video(self, device, idx, total):
        """观看一个视频并随机互动"""
        cfg = self.config

        # 决定观看时长
        watch_time = self._decide_watch_time()
        self._log(device, f"视频 {idx}/{total} (累计 {self._videos_watched + 1}) - 观看 {watch_time:.0f}秒")

        # 等待（模拟观看）
        self.wait(watch_time)
        if self.should_stop:
            return

        simple = cfg.get("simple_mode", True)

        # ── 会切页面的操作：仅在关闭简单模式时才做（这些是跑到Shop/相册的元凶）──
        if not simple:
            if random.random() < cfg["switch_tab_chance"]:
                self._random_tab_switch(device)
            if random.random() < cfg["scroll_comments_chance"]:
                self._browse_comments(device)
            if random.random() < cfg["profile_view_chance"]:
                self._view_profile(device)
            if random.random() < cfg["follow_chance"]:
                self._do_follow(device)

        # ── 点赞：安全动作，两种模式都保留 ──
        # 简单模式下只用双击屏幕中央点赞（推荐页原生手势，不会切页面）
        if random.random() < cfg["like_chance"]:
            if simple:
                self._log(device, "  -> 双击点赞")
                device.double_tap_like()
                self._likes_given += 1
            else:
                self._do_like(device)

        # 滑到下一个视频
        device.swipe_next_video()
        swipe_wait = random.uniform(cfg["swipe_interval_min"], cfg["swipe_interval_max"])
        time.sleep(swipe_wait)

    def _decide_watch_time(self):
        cfg = self.config
        # 完整观看+重播
        if random.random() < cfg["full_watch_chance"]:
            return random.uniform(30, 90)
        # 长时间观看
        if random.random() < cfg["long_watch_chance"]:
            return random.uniform(cfg["long_watch_time_min"], cfg["long_watch_time_max"])
        # 普通观看
        return random.uniform(cfg["watch_time_min"], cfg["watch_time_max"])

    # ── 具体操作 ──

    def _open_tiktok(self, device):
        """可靠打开 TikTok：回桌面 -> 识图找图标点击 -> 验证已进入

        比 URL scheme 更稳，且能确认真的进了 App，避免后续盲点跑飞。
        """
        self._log(device, "打开 TikTok...")
        cfg = self.config
        sim = cfg.get("guard_similarity", 0.7)
        has_icon = os.path.exists(TIKTOK_ICON)

        for attempt in range(3):
            if self.should_stop:
                return
            device.press_home()
            time.sleep(1.5)

            if has_icon:
                loc = device.find_image_file(TIKTOK_ICON, sim)
                if loc:
                    device.tap(loc[0], loc[1])
                else:
                    # 桌面上没找到图标，退回 URL scheme
                    self._log(device, "  未找到桌面图标，用URL方式打开")
                    device.open_tiktok()
            else:
                device.open_tiktok()

            time.sleep(random.uniform(4, 6))

            # 验证：如果还能在屏幕上找到桌面图标，说明没进去，重试
            if has_icon:
                still_home = device.find_image_file(TIKTOK_ICON, sim)
                if still_home:
                    self._log(device, f"  第{attempt+1}次未成功进入，重试")
                    continue
            # 进入后点一下底部首页tab，确保停在信息流（而非上次残留的Shop/主页）
            device.tap_home_tab()
            time.sleep(1.5)
            self._log(device, "  已进入 TikTok 推荐页")
            return
        self._log(device, "  多次尝试后仍未确认进入，继续（依赖识图兜底）")

    def _ensure_tiktok(self, device, force=False):
        """状态守卫：确认当前在 TikTok，跑飞了就拉回。

        防止养号跑飞误入相册的关键。
        force=False（每个视频）：轻量——只在检测到已回桌面时才重开，不打断正常刷视频。
        force=True（每N个视频）：强制干净重进，兜底"卡在相册等其他App"这类无法直接检测的状态。
        """
        if not os.path.exists(TIKTOK_ICON):
            return
        sim = self.config.get("guard_similarity", 0.7)

        if not force:
            # 轻量检测：屏幕上出现桌面 TikTok 图标 = 已回到桌面（跑飞前兆）
            if device.find_image_file(TIKTOK_ICON, sim):
                self._log(device, "⚠ 检测到回到桌面，重新打开 TikTok")
                self._open_tiktok(device)
            return

        # 强制干净重进：无论当前在哪（桌面/相册/其他App），回桌面再进 TikTok
        self._log(device, "定期校准：确保停留在 TikTok")
        self._open_tiktok(device)

    def _do_like(self, device):
        cfg = self.config
        if random.random() < cfg["double_tap_like_chance"]:
            self._log(device, "  -> 双击点赞")
            device.double_tap_like()
        else:
            self._log(device, "  -> 按钮点赞")
            device.tap_like_button()
        self._likes_given += 1
        device.human_wait(cfg["action_interval_min"], cfg["action_interval_max"])

    def _do_follow(self, device):
        self._log(device, "  -> 关注")
        device.tap_follow_button()
        self._follows_given += 1
        device.human_wait(1, 2)

    def _do_search(self, device):
        cfg = self.config
        keyword = random.choice(cfg["search_keywords"])
        self._log(device, f"  -> 搜索: {keyword}")

        device.tap_search()
        time.sleep(1.5)

        # 通过剪贴板输入关键词
        device.send_clipboard(keyword)
        time.sleep(0.5)

        # 点击搜索框，长按粘贴（坐标按机型）
        sb = device.coords.get("search_box", (207, 38))
        device.tap(sb[0], sb[1])
        time.sleep(0.5)

        # 模拟粘贴: fn_key Ctrl+V
        device._post("send_key", {
            "deviceid": device.device_id, "key": "", "fn_key": "CTRL+v",
        })
        time.sleep(0.5)

        # 点击搜索/回车
        device._post("send_key", {
            "deviceid": device.device_id, "key": "ENTER",
        })
        time.sleep(2)

        # 浏览搜索结果
        browse_count = cfg["search_browse_count"]
        for j in range(browse_count):
            if self.should_stop:
                break
            watch = random.uniform(3, 10)
            self._log(device, f"    搜索结果 {j + 1}/{browse_count} 观看 {watch:.0f}秒")
            self.wait(watch)
            device.swipe_next_video()
            time.sleep(1)

        self._searches_done += 1

        # 返回推荐页
        device.tap_back()
        time.sleep(1)
        device.tap_back()
        time.sleep(0.5)
        device.tap_home_tab()
        time.sleep(1.5)

    def _do_rest(self, device):
        cfg = self.config
        rest_time = random.uniform(cfg["rest_time_min"], cfg["rest_time_max"])
        self._log(device, f"  -> 休息 {rest_time:.0f} 秒")
        self.wait(rest_time)

    def _browse_comments(self, device):
        self._log(device, "  -> 浏览评论区")
        device.tap_comment_button()
        time.sleep(1.5)

        scroll_count = random.randint(2, 5)
        for _ in range(scroll_count):
            if self.should_stop:
                break
            device.swipe(200, 600, 200, 350)
            time.sleep(random.uniform(1, 3))

        # 关闭评论区（下滑或点空白区域）
        device.swipe(200, 300, 200, 700)
        time.sleep(1)

    def _view_profile(self, device):
        self._log(device, "  -> 查看发布者主页")
        # 点击头像
        device.tap(random.randint(375, 395), random.randint(220, 240))
        time.sleep(2)

        # 在主页浏览一会
        browse_time = random.uniform(3, 8)
        self.wait(browse_time)

        # 返回
        device.tap_back()
        time.sleep(1.5)

    def _random_tab_switch(self, device):
        tabs = ["discover", "inbox"]
        tab = random.choice(tabs)
        self._log(device, f"  -> 切换到 {tab}")

        if tab == "discover":
            device.tap_discover_tab()
        else:
            device.tap_inbox_tab()

        time.sleep(random.uniform(2, 5))

        # 切回首页
        device.tap_home_tab()
        time.sleep(1.5)

    # ── 辅助方法 ──

    def _log(self, device, msg):
        logger.info(f"[{device.name}] {msg}")

    def _update_progress(self):
        self.progress = {
            "videos_watched": self._videos_watched,
            "likes_given": self._likes_given,
            "follows_given": self._follows_given,
            "searches_done": self._searches_done,
            "sessions_done": self._sessions_done,
        }
