from enum import Enum
from typing import List
from dataclasses import dataclass

# Constants
STICK_LENGTH = 29.0  # length of one pipe stick in feet
POST_HEIGHT = 8.5    # height of posts in feet
POST_SPACING = 8.0   # spacing between posts in feet
STICK_PRICE = 55.0   # price per stick in dollars

class SegmentType(Enum):
    REGULAR = "REGULAR"      # Regular segment with separate start and end posts
    CORNER = "CORNER"        # Segment that ends in a corner (post serves as end of this segment and start of next)

class SectionType(Enum):
    FULL = "FULL"           # Full 8ft section
    PARTIAL = "PARTIAL"     # Partial section at the end of a segment

@dataclass
class Cut:
    length: float
    source_stick: int
    purpose: str  # "POST", "TOP_RAIL", "MID_RAIL"

@dataclass
class Stick:
    id: int
    remaining_length: float
    cuts: List[Cut]

@dataclass
class Section:
    length: float
    type: SectionType
    cuts: List[Cut] = None

@dataclass
class SegmentComponents:
    total_length: float
    num_posts: int
    top_rail_length: float
    top_rail_sticks: float
    mid_rail_sections: int
    sections: List[Section]
    post_cuts: List[Cut] = None
    top_rail_cuts: List[Cut] = None

@dataclass
class ProjectTotals:
    total_post_length: float
    total_top_rail_length: float
    total_mid_rail_length: float
    total_sticks: float
    optimized_sticks: List[Stick] = None
    total_cost: float = 0.0

@dataclass
class FenceSegment:
    length: float
    type: SegmentType
    components: SegmentComponents = None

    def calculate_components(self) -> SegmentComponents:
        """Calculate all components for this segment."""
        # Calculate posts
        num_posts = 1  # Start post
        num_posts += int((self.length - 1) // POST_SPACING)  # Posts every 8ft
        if self.type == SegmentType.REGULAR:
            num_posts += 1  # End post

        # Calculate sections
        sections = []
        full_sections = int(self.length // POST_SPACING)
        last_section = self.length % POST_SPACING

        # Add full sections
        for _ in range(full_sections):
            sections.append(Section(POST_SPACING, SectionType.FULL))
        
        # Add last section if it exists
        if last_section > 0:
            sections.append(Section(last_section, SectionType.PARTIAL))

        return SegmentComponents(
            total_length=self.length,
            num_posts=num_posts,
            top_rail_length=self.length,
            top_rail_sticks=self.length / STICK_LENGTH,
            mid_rail_sections=len(sections),
            sections=sections
        )

def optimize_cuts(segments: List[FenceSegment]) -> List[Stick]:
    """Optimize the cuts to minimize the number of sticks needed."""
    sticks = []
    current_stick_id = 1
    
    # First, collect all required cuts
    all_cuts = []
    
    # Add post cuts
    for segment in segments:
        if segment.components is None:
            segment.components = segment.calculate_components()
        
        # Add post cuts
        for _ in range(segment.components.num_posts):
            all_cuts.append(Cut(POST_HEIGHT, 0, "POST"))
        
        # Add top rail cuts
        remaining_length = segment.length
        while remaining_length > 0:
            if remaining_length >= STICK_LENGTH:
                # For full sticks, just add one cut
                all_cuts.append(Cut(STICK_LENGTH, 0, "TOP_RAIL"))
                remaining_length -= STICK_LENGTH
            else:
                # For partial sticks, add the remaining length
                all_cuts.append(Cut(remaining_length, 0, "TOP_RAIL"))
                remaining_length = 0

    # Sort cuts by length in descending order
    all_cuts.sort(key=lambda x: x.length, reverse=True)
    
    # First pass: Allocate full sticks
    full_stick_cuts = [cut for cut in all_cuts if cut.length == STICK_LENGTH]
    for cut in full_stick_cuts:
        new_stick = Stick(current_stick_id, 0, [cut])  # 0 remaining since it's a full stick
        cut.source_stick = current_stick_id
        sticks.append(new_stick)
        current_stick_id += 1
        all_cuts.remove(cut)
    
    # Second pass: Allocate remaining cuts
    for cut in all_cuts:
        # Try to find a stick with enough remaining length
        assigned = False
        for stick in sticks:
            if stick.remaining_length >= cut.length:
                stick.cuts.append(cut)
                stick.remaining_length -= cut.length
                cut.source_stick = stick.id
                assigned = True
                break
        
        # If no suitable stick found, create a new one
        if not assigned:
            new_stick = Stick(current_stick_id, STICK_LENGTH - cut.length, [cut])
            cut.source_stick = current_stick_id
            sticks.append(new_stick)
            current_stick_id += 1
    
    return sticks

def calculate_project_totals(segments: List[FenceSegment]) -> ProjectTotals:
    """Calculate total materials needed for the entire project."""
    total_post_length = 0
    total_top_rail_length = 0
    total_mid_rail_length = 0

    for segment in segments:
        if segment.components is None:
            segment.components = segment.calculate_components()
        
        total_post_length += segment.components.num_posts * POST_HEIGHT
        total_top_rail_length += segment.components.top_rail_length
        total_mid_rail_length += segment.components.mid_rail_sections * segment.length

    total_sticks = (total_post_length + total_top_rail_length + total_mid_rail_length) / STICK_LENGTH
    
    # Calculate optimized cuts
    optimized_sticks = optimize_cuts(segments)
    
    # Calculate total cost
    total_cost = len(optimized_sticks) * STICK_PRICE

    return ProjectTotals(
        total_post_length=total_post_length,
        total_top_rail_length=total_top_rail_length,
        total_mid_rail_length=total_mid_rail_length,
        total_sticks=total_sticks,
        optimized_sticks=optimized_sticks,
        total_cost=total_cost
    )

def print_material_breakdown(segments: List[FenceSegment], totals: ProjectTotals):
    """Print a detailed breakdown of materials needed."""
    print("\nFENCE CALCULATION SUMMARY")
    print("=" * 40)
    
    print("\nSEGMENT BREAKDOWN:")
    print("-" * 20)
    
    for i, segment in enumerate(segments, 1):
        if segment.components is None:
            segment.components = segment.calculate_components()
            
        print(f"\nSegment {i}: {segment.length} ft ({segment.type.value})")
        print(f"  - Posts: {segment.components.num_posts}")
        print(f"  - Top Rail: {segment.components.top_rail_length} ft ({segment.components.top_rail_sticks:.1f} sticks)")
        print(f"  - Mid Rails: {segment.components.mid_rail_sections} sections")
        
        print("  - Section lengths:")
        for section in segment.components.sections:
            print(f"    * {section.length:.1f} ft")
    
    print("\nTOTAL MATERIALS NEEDED:")
    print("-" * 20)
    print(f"Total Post Length: {totals.total_post_length:.1f} ft")
    print(f"Total Top Rail Length: {totals.total_top_rail_length:.1f} ft")
    print(f"Total Mid Rail Length: {totals.total_mid_rail_length:.1f} ft")
    print(f"\nTotal Length in Sticks: {totals.total_sticks:.1f} sticks (before optimization)")
    
    print("\nOPTIMIZED CUT LIST:")
    print("-" * 20)
    for stick in totals.optimized_sticks:
        print(f"\nStick {stick.id}:")
        total_cut_length = sum(cut.length for cut in stick.cuts)
        print(f"  Total cut length: {total_cut_length:.1f} ft")
        for cut in stick.cuts:
            print(f"  - {cut.length:.1f} ft ({cut.purpose})")
        print(f"  Remaining: {stick.remaining_length:.1f} ft")
    
    print(f"\nTotal Sticks Needed: {len(totals.optimized_sticks)}")
    print(f"Cost per Stick: ${STICK_PRICE:.2f}")
    print(f"Total Cost: ${totals.total_cost:.2f}")

# Example usage
fence_segments = [
    FenceSegment(24.0, SegmentType.REGULAR),
    FenceSegment(108.0, SegmentType.CORNER),
    FenceSegment(15.0, SegmentType.REGULAR),
    FenceSegment(2.0, SegmentType.CORNER),
    FenceSegment(118.5, SegmentType.REGULAR)
]

totals = calculate_project_totals(fence_segments)
print_material_breakdown(fence_segments, totals)
