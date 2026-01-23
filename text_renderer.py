import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import re

def render_latex_to_base64(latex_code, fontsize=12, dpi=120, color='black'):
    """
    Render a LaTeX string to a base64 encoded PNG image.
    
    Args:
        latex_code (str): The LaTeX formula string (e.g., r"$E=mc^2$").
                        Note: Matplotlib usually needs math mode delimiters like $, but we can wrap it if missing.
        fontsize (int): Font size of the formula.
        dpi (int): Dots per inch for the output image.
        color (str): Text color.
        
    Returns:
        str: Base64 encoded string of the PNG image, or None if failed.
    """
    try:
        # Create a figure
        fig = plt.figure(figsize=(0.1, 0.1))
        # Add text - we wrap in $ if not present, though usually regex will strip them or keep them.
        # Matplotlib considers text between $ as math.
        # If the input ALREADY has $, we render as is.
        # Ideally, we want the input to be the raw latex content.
        
        # Clean up the code: strip whitespace and newlines
        cleaned_code = latex_code.strip().replace('\n', ' ')
        
        # Heuristic: if it doesn't start with $, wrap it.
        if not cleaned_code.startswith('$'):
            render_text = f"${cleaned_code}$"
        else:
            render_text = cleaned_code
            
        text = fig.text(0.5, 0.5, render_text, fontsize=fontsize, 
                       ha='center', va='center', color=color)
        
        # Hide axes
        plt.axis('off')
        
        # Draw the canvas to get the bounding box of the text
        # This is necessary to crop the image significantly
        renderer = fig.canvas.get_renderer()
        bbox = text.get_window_extent(renderer=renderer)
        
        # To bbox_inches, we need to convert pixels to inches
        bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())
        
        # Add some padding
        # bbox_inches.x0 -= 0.05
        # bbox_inches.y0 -= 0.05
        # bbox_inches.x1 += 0.05
        # bbox_inches.y1 += 0.05
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=dpi, transparent=True, bbox_inches='tight', pad_inches=0.02)
        plt.close(fig)
        
        buf.seek(0)
        img_bytes = buf.read()
        base64_str = base64.b64encode(img_bytes).decode('utf-8')
        return base64_str
        
    except Exception as e:
        print(f"Error rendering LaTeX: {e}")
        plt.close(fig) if 'fig' in locals() else None
        return None

def process_text_with_formulas(text):
    """
    Scan text for LaTeX patterns and replace them with base64 images.
    
    Supported patterns:
    - $$ ... $$ (Block math)
    - \[ ... \] (Block math)
    - $ ... $ (Inline math) - Note: simple $ matching can be risky with currency.
      We'll try to be careful or strictly support standard delimiters.
      
    For this MVP, we will prioritize standard markdown latex delimiters.
    """
    
    # Placeholder for replacements to avoid recursive mess
    replacements = {}
    
    def replacer(match):
        full_match = match.group(0)
        content = match.group(1)
        
        # Generate a unique key
        key = f"__LATEX_{len(replacements)}__"
        
        # Render
        b64 = render_latex_to_base64(content)
        if b64:
            # Create HTML img tag
            # vertical-align: middle helps inline formulas align better
            img_tag = f'<img src="data:image/png;base64,{b64}" style="vertical-align: middle;">'
            replacements[key] = img_tag
            return key
        else:
            return full_match

    # Regex for $$ ... $$
    # Non-greedy match, handling newlines
    pattern_block_dollar = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
    text = pattern_block_dollar.sub(replacer, text)
    
    # Regex for \[ ... \]
    pattern_block_bracket = re.compile(r'\\\[(.*?)\\\]', re.DOTALL)
    text = pattern_block_bracket.sub(replacer, text)
    
    # Regex for $ ... $
    # We need to be careful not to match simple prices e.g. "Price is $5 and $10"
    # A common heuristic is looking for no space after opening $ and no space before closing $
    # or ensuring the content is math-like.
    # For now, let's use a simpler known pattern provided by LLMs often: $...$
    pattern_inline = re.compile(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', re.DOTALL)
    # text = pattern_inline.sub(replacer, text) 
    # COMMENT: Enabling inline math with single $ risk false positives. 
    # Let's enable it but be cautious or let the user know. 
    # Since this is a specialized AI, it likely outputs correct markdown latex.
    text = pattern_inline.sub(replacer, text)

    # Regex for \( ... \)
    pattern_inline_bracket = re.compile(r'\\\((.*?)\\\)', re.DOTALL)
    text = pattern_inline_bracket.sub(replacer, text)

    # Post-process: substitute keys back with images
    for key, img_tag in replacements.items():
        text = text.replace(key, img_tag)
        
    return text

if __name__ == "__main__":
    # Simple test
    test_str = "Here is a formula: $E=mc^2$ and another one $$ a^2 + b^2 = c^2 $$."
    print("Original:", test_str)
    processed = process_text_with_formulas(test_str)
    print("Processed:", processed[:100], "...")
