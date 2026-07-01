from datetime import datetime, timedelta


class ReviewPolicy:
    """领域服务：只负责艾宾浩斯复习阶段和下次复习时间的计算。"""

    intervals = [0, 1, 3, 7, 15, 30]

    def calculate(self, current_stage: int, remember_level: str) -> tuple[int, datetime]:
        now = datetime.now()

        if remember_level == "known":
            next_stage = min(current_stage + 1, len(self.intervals) - 1)
            return next_stage, now + timedelta(days=self.intervals[next_stage])

        if remember_level == "fuzzy":
            return current_stage, now + timedelta(days=1)

        if remember_level == "unknown":
            return 0, now + timedelta(days=1)

        raise ValueError("rememberLevel must be known, fuzzy, or unknown")
