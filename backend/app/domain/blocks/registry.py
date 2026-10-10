"""Registry of installed drafting blocks, one per garment family version (replaces the single demo profile)."""
from functools import cache

from app.domain.blocks.base import Block, DictBlock, NamedBlock
from app.domain.blocks.demo_shirt import DemoShirtBlock
from app.domain.blocks.shirt.block import ShirtBlock


class BlockRegistry:
    def __init__(self) -> None:
        self._blocks: dict[str, Block] = {}

    def register(self, block: Block) -> Block:
        if block.id in self._blocks:
            raise ValueError(f"Block {block.id} is already registered")
        if block.calibration == "client_approved" and not isinstance(block, NamedBlock):
            raise ValueError(f"Client block {block.id} must draft named points (a NamedBlock)")
        self._blocks[block.id] = block
        return block

    def get(self, block_id: str) -> Block:
        try:
            return self._blocks[block_id]
        except KeyError:
            raise ValueError(f"Drafting block is not installed: {block_id}") from None

    def ids(self, family: str | None = None) -> tuple[str, ...]:
        return tuple(key for key, block in self._blocks.items() if family is None or block.family == family)

    def project_ids(self) -> tuple[str, ...]:
        """Blocks a V5 project can draft with: they draft the V5 dict its grading, markers and exports read."""
        return tuple(key for key, block in self._blocks.items() if isinstance(block, DictBlock))

    def demo(self) -> Block:
        """The block a project falls back to before the user picks one (the demo shirt today)."""
        found = next((block for block in self._blocks.values() if block.calibration == "demo"), None)
        if found is None:
            raise ValueError("No demo-calibration block is installed")
        return found


@cache
def installed() -> BlockRegistry:
    registry = BlockRegistry()
    registry.register(DemoShirtBlock())
    registry.register(ShirtBlock())
    return registry


def demo_block() -> Block:
    return installed().demo()
