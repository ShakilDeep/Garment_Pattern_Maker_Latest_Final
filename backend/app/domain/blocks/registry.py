"""Registry of installed drafting blocks, one per garment family version (replaces the single demo profile)."""
from functools import cache

from app.domain.blocks.base import Block, NamedBlock
from app.domain.blocks.demo_shirt import DemoShirtBlock
from app.domain.blocks.shirt.block import ShirtBlock
from app.domain.blocks.shirt_v2 import ShirtV2Block


class BlockRegistry:
    def __init__(self, fallback: str | None = None) -> None:
        self._blocks: dict[str, Block] = {}
        self._fallback = fallback  # the block a project drafts with before the user picks one

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
        """Blocks a project can draft with: every installed block, as the drafting engine gives each the
        V5 dict its views read (T141) and the chart or reference values it needs (T142)."""
        return tuple(self._blocks)

    def demo(self) -> Block:
        """The block a project falls back to before the user picks one: the named fallback when installed,
        else the first demo-calibration block."""
        if self._fallback in self._blocks:
            return self._blocks[self._fallback]
        found = next((block for block in self._blocks.values() if block.calibration == "demo"), None)
        if found is None:
            raise ValueError("No demo-calibration block is installed")
        return found


@cache
def installed() -> BlockRegistry:
    # The client 1078375 block (owner, 2026-10-13): a project drafts the seven PDS pieces; shirt_v2 and demo_v1
    # stay selectable.
    registry = BlockRegistry(fallback="shirt_1078375")
    registry.register(DemoShirtBlock())
    registry.register(ShirtBlock())
    registry.register(ShirtV2Block())
    return registry


def demo_block() -> Block:
    return installed().demo()
