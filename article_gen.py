#!/usr/bin/env python3
"""
Article Generator for MagicLookBook.com Content Center
Generates SEO-optimized articles using Gemini 2.5 Flash and creates images using nano-banana
"""

import os
import json
import time
import requests
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ArticleGenerator:
    def __init__(self, force_regenerate=False):
        # Initialize Gemini client
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        self.force_regenerate = force_regenerate
        
        # Article categories and topics (as per instruction.md)
        self.categories = {
            "occasions": [
                "cocktail-attire-guide",
                "wedding-attire-guide", 
                "funeral-attire-guide",
                "gala-attire-guide",
                "date-outfit-guide"
            ],
            "events": [
                "concert-outfit-guide",
                "festival-outfit-guide",
                "movie-outfit-guide",
                "beach-outfit-guide",
                "sporting-event-outfit-guide"
            ],
            "seasonal": [
                "summer-outfit-guide",
                "fall-outfit-guide",
                "winter-outfit-guide",
                "spring-outfit-guide",
                "holiday-party-outfit-guide"
            ],
            "professional": [
                "business-casual-guide",
                "job-interview-outfit-guide",
                "conference-outfit-guide",
                "networking-event-outfit-guide",
                "presentation-outfit-guide"
            ]
        }
        
    def generate_article_outline(self, topic: str, category: str) -> Dict:
        """Generate article outline using Gemini"""
        prompt = f"""
        Create a comprehensive article outline for "{topic.replace('-', ' ').title()}" in the {category} category.
        
        The article should be SEO-optimized for MagicLookBook.com, a fashion and style content site.
        
        Return a JSON object with:
        1. "title": SEO-friendly title (60 chars max)
        2. "description": Meta description (155 chars max)
        3. "keywords": List of 3-5 target keywords
        4. "sections": List of article sections, each with:
           - "heading": Section H2 heading
           - "content_points": List of 3-4 bullet points to cover
        5. "images": List of 3-4 images, each with:
           - "filename": Descriptive filename without extension (e.g., "woman-cocktail-dress", "elegant-party-scene")
           - "alt_text": Descriptive alt text for the image
           - "prompt": Detailed photorealistic image generation prompt for fashion/style photography. Include:
             * Start with "A photo of..." for photorealistic results
             * Specify lighting (e.g., golden hour, studio lighting, natural light)
             * Include camera details (e.g., 85mm portrait lens, 35mm lens)
             * Mention styling details (colors, fabrics, accessories)
             * Describe the scene/background
           - "aspect_ratio": One of "16:9" (widescreen), "1:1" (square), "3:4" (portrait), "4:3" (fullscreen)
           - "placement_after_section": Section index after which to place this image (0 for after intro, 1 for after first section, etc.)
        6. "related_topics": List of 3-4 related article topics from other categories
        """
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )
        
        return json.loads(response.text)
    
    def generate_article_content(self, topic: str, category: str, outline: Dict) -> str:
        """Generate full article content based on outline"""
        # Prepare image references for the content
        image_refs = []
        for img in outline.get('images', []):
            image_refs.append({
                "markdown": f"![{img['alt_text']}](/content/images/{category}/{img['filename']}.png)",
                "placement_after_section": img['placement_after_section']
            })
        
        prompt = f"""
        Write a comprehensive, SEO-optimized article based on this outline:
        
        Topic: {topic.replace('-', ' ').title()}
        Title: {outline['title']}
        Keywords: {', '.join(outline['keywords'])}
        
        Sections to cover:
        {json.dumps(outline['sections'], indent=2)}
        
        Image placements:
        {json.dumps(image_refs, indent=2)}
        
        Requirements:
        1. Write in a friendly, informative tone
        2. Each section should be 150-200 words
        3. Include practical tips and advice
        4. Make it engaging and helpful for readers
        5. Use the keywords naturally throughout
        6. Insert the provided image markdown references at the specified locations
        7. Add a "Related Articles" section at the end with links to related topics
        
        Format as markdown with proper headings (# for title, ## for sections).
        Place images after the specified sections based on the placement_after_section index.
        """
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048
            )
        )
        
        return response.text
    
    def generate_image_with_imagen(self, prompt: str, filename: str, aspect_ratio: str = "16:9") -> bool:
        """Generate image using Gemini's Imagen API"""
        # Check if image already exists
        image_path = Path(filename)
        if image_path.exists() and not self.force_regenerate:
            print(f"    ✓ Image already exists: {filename}")
            return True
        
        print(f"    → Generating image: {filename}")
        print(f"      Aspect ratio: {aspect_ratio}")
        print(f"      Prompt: {prompt[:80]}...")
        
        try:
            # Generate image using Gemini's Imagen model
            response = self.client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    safety_filter_level="BLOCK_LOW_AND_ABOVE",
                    person_generation="ALLOW_ADULT",
                    aspect_ratio=aspect_ratio
                )
            )
            
            # Save the generated image
            if response.generated_images:
                generated_image = response.generated_images[0]
                # Ensure directory exists
                image_path.parent.mkdir(parents=True, exist_ok=True)
                # Write the image bytes to file
                image_path.write_bytes(generated_image.image.image_bytes)
                print(f"    ✓ Image saved: {filename}")
                return True
            else:
                print(f"    ❌ No image generated for: {filename}")
                return False
                
        except Exception as e:
            print(f"    ❌ Error generating image: {str(e)}")
            # Continue with article generation even if image fails
            return False
    
    def create_article_file(self, topic: str, category: str, content: str, outline: Dict):
        """Create the markdown file with frontmatter"""
        # Create frontmatter
        frontmatter = f"""---
layout: layouts/base.njk
title: "{outline['title']}"
description: "{outline['description']}"
keywords: "{', '.join(outline['keywords'])}"
ogImage: "/content/images/{category}/{topic}-hero.png"
---

"""
        
        # Add keywords and meta description at the end
        footer = f"""

**Keywords:** {', '.join(outline['keywords'])}

**Meta Description:** {outline['description']}
"""
        
        # Combine all parts
        full_content = frontmatter + content + footer
        
        # Create directory if it doesn't exist
        content_dir = Path("content")
        content_dir.mkdir(exist_ok=True)
        
        # Write file
        file_path = content_dir / f"{topic}.md"
        file_path.write_text(full_content)
        print(f"  ✓ Created article: {file_path}")
        
        # Create image directory
        image_dir = Path("content/images") / category
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate images based on the outline
        if 'images' in outline:
            # New format with filenames
            for img in outline['images']:
                image_filename = f"{img['filename']}.png"
                image_path = image_dir / image_filename
                aspect_ratio = img.get('aspect_ratio', '16:9')  # Default to widescreen
                self.generate_image_with_imagen(img['prompt'], str(image_path), aspect_ratio)
        elif 'image_prompts' in outline:
            # Legacy format for backward compatibility
            print("  ⚠️  Using legacy image format (no specific filenames)")
            for i, prompt in enumerate(outline['image_prompts']):
                image_name = f"{topic}-{i+1}.png" if i > 0 else f"{topic}-hero.png"
                self.generate_image_with_imagen(prompt, str(image_dir / image_name), '16:9')
    
    def generate_all_articles(self):
        """Generate all articles for all categories"""
        all_articles = []
        skipped_count = 0
        generated_count = 0
        
        for category, topics in self.categories.items():
            print(f"\nProcessing category: {category}")
            
            for topic in topics:
                print(f"\n📄 Topic: {topic}")
                
                # Check if article already exists
                article_path = Path("content") / f"{topic}.md"
                if article_path.exists() and not self.force_regenerate:
                    print(f"  ✓ Article already exists: {article_path}")
                    skipped_count += 1
                    
                    # Still add to index for existing articles
                    try:
                        with open(article_path, 'r') as f:
                            content = f.read()
                            # Extract title from frontmatter
                            title_line = [line for line in content.split('\n') if line.startswith('title:')][0]
                            title = title_line.split('"')[1]
                            
                            # Extract keywords from content
                            keywords_line = [line for line in content.split('\n') if line.startswith('keywords:')][0]
                            keywords = [k.strip() for k in keywords_line.split('"')[1].split(',')]
                            
                            all_articles.append({
                                "topic": topic,
                                "category": category,
                                "title": title,
                                "keywords": keywords
                            })
                    except:
                        # If we can't parse existing file, skip it
                        pass
                    continue
                
                try:
                    # Generate outline
                    print("  → Generating outline...")
                    outline = self.generate_article_outline(topic, category)
                    
                    # Generate content
                    print("  → Generating content...")
                    content = self.generate_article_content(topic, category, outline)
                    
                    # Create article file and generate images immediately
                    print("  → Creating article and images...")
                    self.create_article_file(topic, category, content, outline)
                    
                    all_articles.append({
                        "topic": topic,
                        "category": category,
                        "title": outline['title'],
                        "keywords": outline['keywords']
                    })
                    
                    generated_count += 1
                    
                    # Rate limiting to avoid API limits
                    if generated_count > 0:
                        print("  ⏱️  Waiting 2 seconds (rate limit)...")
                        time.sleep(2)
                    
                except Exception as e:
                    print(f"  ❌ ERROR: {str(e)}")
                    continue
        
        # Save article index for reference
        with open("article_index.json", "w") as f:
            json.dump(all_articles, f, indent=2)
        
        print(f"\n✅ Summary:")
        print(f"  - Generated: {generated_count} articles")
        print(f"  - Skipped: {skipped_count} existing articles")
        print(f"  - Total indexed: {len(all_articles)} articles")
        
        return all_articles
    
    def update_cross_references(self):
        """Update articles to reference each other properly"""
        print("\nUpdating cross-references between articles...")
        
        # This would scan all articles and update the [[Article Name]] references
        # to proper markdown links based on the actual file names
        
        content_dir = Path("content")
        for md_file in content_dir.glob("*.md"):
            content = md_file.read_text()
            
            # Simple replacement of [[Title]] with [Title](/content/topic-name/)
            # In production, you'd want more sophisticated matching
            
            # For now, just print what would be updated
            if "[[" in content:
                print(f"  Would update references in: {md_file.name}")

def main():
    """Main execution function"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Generate SEO-optimized articles for MagicLookBook.com"
    )
    parser.add_argument(
        "--all", 
        action="store_true",
        help="Force regeneration of all articles and images, even if they already exist"
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Generate only a specific topic (e.g., 'cocktail-attire-guide')"
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["occasions", "events", "seasonal", "professional"],
        help="Generate only articles in a specific category"
    )
    
    args = parser.parse_args()
    
    print("MagicLookBook.com Article Generator")
    print("=" * 40)
    
    if args.all:
        print("🔄 Force regeneration mode: ON")
    
    # Create generator instance
    generator = ArticleGenerator(force_regenerate=args.all)
    
    # Filter topics if specific topic or category requested
    if args.topic:
        # Find which category the topic belongs to
        topic_found = False
        for cat, topics in generator.categories.items():
            if args.topic in topics:
                generator.categories = {cat: [args.topic]}
                topic_found = True
                print(f"📌 Generating only: {args.topic}")
                break
        if not topic_found:
            print(f"❌ Error: Topic '{args.topic}' not found!")
            print("Available topics:")
            for cat, topics in generator.categories.items():
                print(f"  {cat}: {', '.join(topics)}")
            return
    elif args.category:
        generator.categories = {args.category: generator.categories[args.category]}
        print(f"📁 Generating only category: {args.category}")
    
    # Generate all articles
    articles = generator.generate_all_articles()
    
    # Update cross-references
    generator.update_cross_references()
    
    print("\n✅ Article generation complete!")
    
    # Create a simple index.html if needed
    index_content = """# MagicLookBook Content Center

Welcome to our comprehensive style and fashion guide collection!

## Categories

### Occasions
- [Cocktail Attire Guide](/content/cocktail-attire-guide/)
- [Wedding Attire Guide](/content/wedding-attire-guide/)
- [Funeral Attire Guide](/content/funeral-attire-guide/)
- [Gala Attire Guide](/content/gala-attire-guide/)
- [Date Outfit Guide](/content/date-outfit-guide/)

### Events
- [Concert Outfit Guide](/content/concert-outfit-guide/)
- [Festival Outfit Guide](/content/festival-outfit-guide/)
- [Movie Outfit Guide](/content/movie-outfit-guide/)
- [Beach Outfit Guide](/content/beach-outfit-guide/)
- [Sporting Event Outfit Guide](/content/sporting-event-outfit-guide/)

### Seasonal
- [Summer Outfit Guide](/content/summer-outfit-guide/)
- [Fall Outfit Guide](/content/fall-outfit-guide/)
- [Winter Outfit Guide](/content/winter-outfit-guide/)
- [Spring Outfit Guide](/content/spring-outfit-guide/)
- [Holiday Party Outfit Guide](/content/holiday-party-outfit-guide/)

### Professional
- [Business Casual Guide](/content/business-casual-guide/)
- [Job Interview Outfit Guide](/content/job-interview-outfit-guide/)
- [Conference Outfit Guide](/content/conference-outfit-guide/)
- [Networking Event Outfit Guide](/content/networking-event-outfit-guide/)
- [Presentation Outfit Guide](/content/presentation-outfit-guide/)
"""
    
    with open("content/index.md", "w") as f:
        f.write(index_content)
    
    print("\n📝 Created content index")

if __name__ == "__main__":
    main()
