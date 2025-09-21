# Article Generator for MagicLookBook.com

This Python script generates SEO-optimized fashion and style articles using Google's Gemini 2.5 Flash API and creates images using Gemini's Imagen API.

## Features

- Generates 20 articles across 4 categories (occasions, events, seasonal, professional)
- Creates SEO-optimized content with proper keywords and meta descriptions
- Generates article outlines with AI before creating full content
- Generates photorealistic fashion/style images using Gemini's Imagen API
- Supports cross-referencing between related articles
- Follows the exact format of existing articles (like cocktail-attire-guide.md)
- **Smart regeneration**: Skips existing articles/images unless `--all` flag is used
- **Sequential generation**: Generates each article with its images before moving to the next
- **Flexible generation**: Can generate single topics, categories, or everything
- **Consistent image naming**: Images get descriptive filenames that match references in articles

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys:
```env
# Gemini API Key - Get from https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your Gemini API key from: https://aistudio.google.com/app/apikey

3. Run the generator:
```bash
# Generate only new articles (skip existing ones)
python article_gen.py

# Force regenerate all articles and images
python article_gen.py --all

# Generate only a specific topic
python article_gen.py --topic cocktail-attire-guide

# Generate only a specific category
python article_gen.py --category seasonal
```

## Output

The script will create:
- `content/` directory with all markdown articles
- `content/images/` directory structure for images (organized by category)
- `article_index.json` with metadata about all generated articles

## Article Structure

Each generated article includes:
- SEO-optimized title and meta description
- Target keywords
- Multiple content sections with H2 headings
- Image placeholders with descriptive alt text
- Related articles section
- Proper frontmatter for 11ty static site generator

## Categories and Topics

### Occasions
- Cocktail Attire Guide
- Wedding Attire Guide
- Funeral Attire Guide
- Gala Attire Guide
- Date Outfit Guide

### Events
- Concert Outfit Guide
- Festival Outfit Guide
- Movie Outfit Guide
- Beach Outfit Guide
- Sporting Event Outfit Guide

### Seasonal
- Summer Outfit Guide
- Fall Outfit Guide
- Winter Outfit Guide
- Spring Outfit Guide
- Holiday Party Outfit Guide

### Professional
- Business Casual Guide
- Job Interview Outfit Guide
- Conference Outfit Guide
- Networking Event Outfit Guide
- Presentation Outfit Guide

## Image Generation

The script generates images with descriptive filenames that match the references in articles:

### Image Naming System
- Images are stored in `/content/images/{category}/` directories
- Each image gets a descriptive filename (e.g., `woman-cocktail-dress.png`, `outdoor-festival-crowd.png`)
- The outline phase determines both the image prompts AND filenames
- Article content automatically references the correct image paths

### Example Image Structure
```
content/images/
├── occasions/
│   ├── woman-cocktail-dress.png
│   ├── elegant-party-scene.png
│   └── mens-formal-attire.png
├── events/
│   ├── outdoor-festival-crowd.png
│   ├── concert-venue-style.png
│   └── festival-essentials.png
└── seasonal/
    ├── summer-beach-outfit.png
    └── winter-layering-guide.png
```

### Gemini Imagen API Integration
The script now uses Gemini's Imagen API for image generation:
- Uses **imagen-4.0-generate-001** model for high-quality fashion/style images
- Supports multiple aspect ratios (16:9, 1:1, 3:4, 4:3) based on content type
- Generates photorealistic images with professional photography styling
- Images are saved with descriptive filenames determined during outline generation

The image generation is fully integrated and will work with your existing GEMINI_API_KEY.

### Image Prompt Tips for Better Results
The outline generator is configured to create photorealistic prompts that include:
- Starting with "A photo of..." for photorealistic results
- Specific lighting conditions (golden hour, studio lighting, etc.)
- Camera details (85mm portrait lens, 35mm lens, etc.)
- Fashion styling details (colors, fabrics, accessories)
- Background and scene descriptions

## Rate Limiting

The script includes a 2-second delay between API calls to avoid rate limits. Adjust as needed based on your API plan.

## Customization

You can modify:
- Categories and topics in the `__init__` method
- Article structure in `generate_article_outline()`
- Content style in `generate_article_content()`
- Temperature and other AI parameters for different creative outputs
