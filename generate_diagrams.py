#!/usr/bin/env python3
"""
PwnGPT Architecture Diagrams Generator

Creates two professional Draw.io diagrams:
1. The Agentic Loop: Observe -> Reason -> Act -> Verify (horizontal flowchart with loop)
2. The Fortress Architecture: Layered diagram showing Gemini 3 LLM -> Guardian Protocol -> Docker Sandbox

Uses cyber color palette:
- Background: #0D1117
- Accents/Text: #00FF41  
- Boxes: #1F2937

Applies rounded=1 and shadow=1 styles for modern look.
"""

from drawio_diagram_generator import (
    Box, Arrow, Row, Column, Group, Diagram, build_style_string
)
import subprocess
import os

# ============================================================================
# Cyber Color Palette
# ============================================================================
CYBER_BG = "#0D1117"       # Dark background
CYBER_ACCENT = "#00FF41"   # Neon green accent
CYBER_BOX = "#1F2937"      # Dark gray boxes
CYBER_TEXT = "#00FF41"     # Neon green text

# Common style elements
MODERN_STYLE = "rounded=1;shadow=1;"


def create_agentic_loop_diagram():
    """
    Creates the Agentic Loop diagram:
    Observe -> Reason -> Act -> Verify with a Loop arrow back to Observe
    """
    
    # Box style for cyber look
    box_style = build_style_string(
        fillColor=CYBER_BOX,
        strokeColor=CYBER_ACCENT,
        fontColor=CYBER_TEXT,
        rounded="1",
        shadow="1",
        strokeWidth="2",
        fontSize="14",
        fontStyle="1",  # Bold
    )
    
    # Arrow style
    arrow_style = build_style_string(
        strokeColor=CYBER_ACCENT,
        strokeWidth="2",
        fontColor=CYBER_TEXT,
        fontSize="11",
    )
    
    # Loop arrow style (curved, dashed for distinction)
    loop_arrow_style = build_style_string(
        strokeColor=CYBER_ACCENT,
        strokeWidth="3",
        fontColor=CYBER_TEXT,
        fontSize="12",
        dashed="1",
        dashPattern="5 3",
        curved="1",
    )
    
    # Title box style
    title_style = build_style_string(
        fillColor="none",
        strokeColor="none",
        fontColor=CYBER_ACCENT,
        fontSize="20",
        fontStyle="1",  # Bold
    )

    # Create the main boxes
    observe = Box("🔍 OBSERVE", width=140, height=70, style=box_style)
    reason = Box("🧠 REASON", width=140, height=70, style=box_style)
    act = Box("⚡ ACT", width=140, height=70, style=box_style)
    verify = Box("✅ VERIFY", width=140, height=70, style=box_style)
    
    # Title
    title = Box("THE AGENTIC LOOP", width=300, height=50, style=title_style)

    # Create the horizontal row of boxes
    flow_row = Row([observe, reason, act, verify], spacing=80, align="middle")
    
    # Arrows between boxes
    arrow1 = Arrow(observe, reason, label="", style=arrow_style, direction="LR")
    arrow2 = Arrow(reason, act, label="", style=arrow_style, direction="LR")
    arrow3 = Arrow(act, verify, label="", style=arrow_style, direction="LR")
    
    # Loop arrow from Verify back to Observe
    loop_arrow = Arrow(verify, observe, label="LOOP", style=loop_arrow_style, direction="LR")
    
    # Create the main layout
    main_layout = Column([title, flow_row], spacing=40, align="center")
    
    # Create a group with all components
    diagram_group = Group(
        "",
        [main_layout],
        layout="column",
        align="center",
        spacing=20,
        padding=50,
        other_components=[arrow1, arrow2, arrow3, loop_arrow],
        style_opts={
            "fillColor": CYBER_BG,
            "strokeColor": CYBER_ACCENT,
            "rounded": "1",
            "shadow": "1",
            "strokeWidth": "2",
        },
        is_root=True
    )
    
    return Diagram(diagram_group)


def create_fortress_diagram():
    """
    Creates the Fortress Architecture diagram:
    Layered diagram showing Gemini 3 LLM at top, Guardian Protocol in middle,
    Docker Sandbox at bottom.
    """
    
    # Top layer style (LLM - brain/intelligence)
    llm_style = build_style_string(
        fillColor="#1a1f4c",  # Deep blue for AI
        strokeColor=CYBER_ACCENT,
        fontColor="#FFFFFF",
        rounded="1",
        shadow="1",
        strokeWidth="2",
        fontSize="16",
        fontStyle="1",
    )
    
    # Middle layer style (Guardian - security/firewall)
    guardian_style = build_style_string(
        fillColor="#7f1d1d",  # Deep red for security
        strokeColor=CYBER_ACCENT,
        fontColor="#FFFFFF",
        rounded="1",
        shadow="1", 
        strokeWidth="3",
        fontSize="16",
        fontStyle="1",
    )
    
    # Bottom layer style (Docker - containment)
    docker_style = build_style_string(
        fillColor=CYBER_BOX,
        strokeColor=CYBER_ACCENT,
        fontColor=CYBER_TEXT,
        rounded="1",
        shadow="1",
        strokeWidth="2",
        fontSize="16",
        fontStyle="1",
    )
    
    # Title style
    title_style = build_style_string(
        fillColor="none",
        strokeColor="none",
        fontColor=CYBER_ACCENT,
        fontSize="20",
        fontStyle="1",
    )
    
    # Label style for layer descriptions
    label_style = build_style_string(
        fillColor="none",
        strokeColor="none",
        fontColor="#888888",
        fontSize="11",
        fontStyle="2",  # Italic
    )
    
    # Arrow style (vertical data flow)
    arrow_style = build_style_string(
        strokeColor=CYBER_ACCENT,
        strokeWidth="2",
        fontColor=CYBER_TEXT,
        fontSize="10",
    )
    
    # Title
    title = Box("THE FORTRESS ARCHITECTURE", width=400, height=50, style=title_style)
    
    # Create the layered boxes
    llm_box = Box("🧠 GEMINI 3 LLM", width=350, height=80, style=llm_style)
    llm_label = Box("Intelligence Layer", width=350, height=30, style=label_style)
    
    guardian_box = Box("🛡️ GUARDIAN PROTOCOL", width=400, height=90, style=guardian_style)
    guardian_label = Box("Security Firewall & Filter", width=400, height=30, style=label_style)
    
    docker_box = Box("🐳 DOCKER SANDBOX", width=350, height=80, style=docker_style)
    docker_label = Box("Isolated Execution (Kali Linux)", width=350, height=30, style=label_style)
    
    # Create vertical layers
    llm_layer = Column([llm_box, llm_label], spacing=5, align="center")
    guardian_layer = Column([guardian_box, guardian_label], spacing=5, align="center")
    docker_layer = Column([docker_box, docker_label], spacing=5, align="center")
    
    # Stack layers vertically
    layers = Column([llm_layer, guardian_layer, docker_layer], spacing=40, align="center")
    
    # Arrows showing flow
    arrow_down1 = Arrow(llm_box, guardian_box, label="Commands", style=arrow_style, direction="TB")
    arrow_down2 = Arrow(guardian_box, docker_box, label="Safe Cmds", style=arrow_style, direction="TB")
    
    # Main layout
    main_layout = Column([title, layers], spacing=30, align="center")
    
    # Create group with all components
    diagram_group = Group(
        "",
        [main_layout],
        layout="column",
        align="center",
        spacing=20,
        padding=60,
        other_components=[arrow_down1, arrow_down2],
        style_opts={
            "fillColor": CYBER_BG,
            "strokeColor": CYBER_ACCENT,
            "rounded": "1",
            "shadow": "1",
            "strokeWidth": "2",
        },
        is_root=True
    )
    
    return Diagram(diagram_group)


def export_to_png(drawio_path, png_path):
    """
    Export .drawio file to .png using draw.io CLI if available.
    Falls back to informing user if CLI not installed.
    """
    # Try using draw.io CLI (installed as part of draw.io desktop)
    drawio_cli_paths = [
        "/Applications/draw.io.app/Contents/MacOS/draw.io",
        "/opt/homebrew/bin/draw.io",
        "draw.io",
        "drawio"
    ]
    
    for cli_path in drawio_cli_paths:
        try:
            result = subprocess.run(
                [cli_path, "-x", "-f", "png", "-o", png_path, drawio_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    
    return False


def main():
    print("=" * 60)
    print("🎨 PwnGPT Architecture Diagram Generator")
    print("=" * 60)
    
    output_dir = "/Users/mac/Desktop/PwnGPT/diagrams"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate Agentic Loop Diagram
    print("\n📊 Creating 'The Agentic Loop' diagram...")
    agentic_diagram = create_agentic_loop_diagram()
    agentic_drawio_path = os.path.join(output_dir, "agentic_loop.drawio")
    agentic_diagram.save(agentic_drawio_path)
    print(f"   ✅ Saved: {agentic_drawio_path}")
    
    # Generate Fortress Architecture Diagram  
    print("\n🏰 Creating 'The Fortress Architecture' diagram...")
    fortress_diagram = create_fortress_diagram()
    fortress_drawio_path = os.path.join(output_dir, "fortress_architecture.drawio")
    fortress_diagram.save(fortress_drawio_path)
    print(f"   ✅ Saved: {fortress_drawio_path}")
    
    # Try to export to PNG
    print("\n🖼️  Attempting PNG export...")
    
    agentic_png_path = os.path.join(output_dir, "agentic_loop.png")
    if export_to_png(agentic_drawio_path, agentic_png_path):
        print(f"   ✅ PNG exported: {agentic_png_path}")
    else:
        print("   ⚠️  PNG export requires draw.io desktop app")
        print("      Install from: https://www.drawio.com/")
        print("      Or open .drawio files and export manually")
    
    fortress_png_path = os.path.join(output_dir, "fortress_architecture.png")
    if export_to_png(fortress_drawio_path, fortress_png_path):
        print(f"   ✅ PNG exported: {fortress_png_path}")
    
    print("\n" + "=" * 60)
    print("✨ Diagram generation complete!")
    print(f"📁 Output directory: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
