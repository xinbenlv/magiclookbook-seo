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
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Semaphore
import random
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ArticleGenerator:
    def __init__(self, force_regenerate=False, max_concurrent=5):
        # Initialize Gemini client
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        self.force_regenerate = force_regenerate
        self.max_concurrent = max_concurrent
        
        # Thread safety for shared resources
        self.print_lock = Lock()
        self.stats_lock = Lock()
        
        # Rate limiting semaphore to prevent API overload
        self.api_semaphore = Semaphore(min(max_concurrent, 5))  # Limit concurrent API calls
        
        # Create outlines directory
        self.outlines_dir = Path("outlines")
        self.outlines_dir.mkdir(exist_ok=True)
        
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
    
    def safe_print(self, message: str) -> None:
        """Thread-safe printing"""
        with self.print_lock:
            print(message)
    
    def rate_limited_api_call(self, func, *args, **kwargs):
        """Execute API call with rate limiting and retry logic"""
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Acquire semaphore to limit concurrent API calls
                with self.api_semaphore:
                    # Add random jitter to prevent thundering herd
                    jitter = random.uniform(0.1, 0.5)
                    time.sleep(jitter)
                    
                    # Make the API call
                    return func(*args, **kwargs)
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for rate limiting or SSL errors
                if any(keyword in error_msg for keyword in ['ssl', 'tls', 'decode', 'rate', 'limit', 'quota']):
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        delay = base_delay * (2 ** attempt) + random.uniform(0.5, 1.5)
                        self.safe_print(f"    ⚠️  API error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}...")
                        self.safe_print(f"    ⏱️  Retrying in {delay:.1f} seconds...")
                        time.sleep(delay)
                        continue
                
                # If it's not a retryable error or we've exhausted retries
                raise e
        
        raise Exception(f"API call failed after {max_retries} attempts")
    
    def get_outline_path(self, topic: str, category: str) -> Path:
        """Get the path for storing outline file"""
        category_dir = self.outlines_dir / category
        category_dir.mkdir(exist_ok=True)
        return category_dir / f"{topic}.yml"
    
    def save_outline(self, topic: str, category: str, outline: Dict) -> None:
        """Save outline to YAML file"""
        outline_path = self.get_outline_path(topic, category)
        
        # Add metadata to outline
        outline_with_meta = {
            "topic": topic,
            "category": category,
            "generated_at": datetime.now().isoformat(),
            **outline
        }
        
        with open(outline_path, 'w') as f:
            yaml.dump(outline_with_meta, f, default_flow_style=False, sort_keys=False)
        
        self.safe_print(f"  ✓ Saved outline: {outline_path}")
    
    def load_outline(self, topic: str, category: str) -> Optional[Dict]:
        """Load outline from YAML file"""
        outline_path = self.get_outline_path(topic, category)
        
        if not outline_path.exists():
            return None
        
        try:
            with open(outline_path, 'r') as f:
                outline = yaml.safe_load(f)
            self.safe_print(f"  ✓ Loaded outline: {outline_path}")
            return outline
        except Exception as e:
            self.safe_print(f"  ❌ Error loading outline: {e}")
            return None
    
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
        6. CRITICAL: Use ONLY the exact image markdown references provided in the "Image placements" section above. Do NOT create your own image references or modify the provided ones.
        7. Insert the provided image markdown references at the specified locations exactly as given
        8. Add a "Related Articles" section at the end with links to related topics
        
        Format as markdown with proper headings (# for title, ## for sections).
        IMPORTANT: Use only the image markdown references from the "Image placements" section - do not create new ones.
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
            # Generate image using Gemini's Imagen model with rate limiting
            response = self.rate_limited_api_call(
                self.client.models.generate_images,
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
    
    def create_article_file_only(self, topic: str, category: str, content: str, outline: Dict):
        """Create only the markdown file with frontmatter (no image generation)"""
        # Dynamically set ogImage to the first image in the outline
        og_image_path = ""
        if 'images' in outline and outline['images']:
            hero_image_filename = outline['images'][0]['filename']
            og_image_path = f"/content/images/{category}/{hero_image_filename}.png"
        
        # Create frontmatter
        frontmatter = f"""---
layout: layouts/base.njk
title: "{outline['title']}"
description: "{outline['description']}"
keywords: "{', '.join(outline['keywords'])}"
ogImage: "{og_image_path}"
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
    
    def check_missing_images(self, category: str, outline: Dict) -> List[Dict]:
        """Check which images from the outline are missing on disk"""
        if 'images' not in outline:
            return []
        
        image_dir = Path("content/images") / category
        missing_images = []
        
        for img in outline['images']:
            image_filename = f"{img['filename']}.png"
            image_path = image_dir / image_filename
            if not image_path.exists():
                missing_images.append(img)
        
        return missing_images
    
    def analyze_cross_references(self) -> None:
        """Analyze all outlines and update cross-references"""
        self.safe_print("\n🔗 Analyzing cross-references between articles...")
        
        # Load all outlines
        all_outlines = {}
        for category, topics in self.categories.items():
            for topic in topics:
                outline = self.load_outline(topic, category)
                if outline:
                    all_outlines[topic] = outline
        
        # Update cross-references for each outline
        for topic, outline in all_outlines.items():
            category = outline['category']
            
            # Find related topics based on keywords and content similarity
            related_topics = self.find_related_topics(topic, outline, all_outlines)
            
            if related_topics:
                # Update outline with cross-references
                outline['related_topics'] = related_topics
                self.save_outline(topic, category, outline)
                self.safe_print(f"  ✓ Updated cross-references for: {topic}")
    
    def find_related_topics(self, current_topic: str, current_outline: Dict, all_outlines: Dict) -> List[str]:
        """Find related topics for cross-referencing"""
        current_keywords = set(current_outline.get('keywords', []))
        current_category = current_outline['category']
        
        related_topics = []
        
        # Find topics with overlapping keywords (excluding current topic)
        for topic, outline in all_outlines.items():
            if topic == current_topic:
                continue
                
            topic_keywords = set(outline.get('keywords', []))
            
            # Calculate keyword overlap
            overlap = len(current_keywords.intersection(topic_keywords))
            
            # Add if there's significant overlap or if it's from a different category
            if overlap >= 1 or outline['category'] != current_category:
                related_topics.append(topic)
        
        # Limit to 3-4 related topics
        return related_topics[:4]
    
    def generate_images_from_outline(self, topic: str, category: str, outline: Dict) -> int:
        """Generate images based on outline data, returns count of images generated"""
        if 'images' not in outline:
            return 0
        
        # Create image directory
        image_dir = Path("content/images") / category
        image_dir.mkdir(parents=True, exist_ok=True)
        
        images_generated = 0
        for img in outline['images']:
            image_filename = f"{img['filename']}.png"
            image_path = image_dir / image_filename
            aspect_ratio = img.get('aspect_ratio', '16:9')  # Default to widescreen
            if self.generate_image_with_imagen(img['prompt'], str(image_path), aspect_ratio):
                images_generated += 1
        
        return images_generated
    
    def generate_single_outline(self, topic: str, category: str) -> Dict:
        """Generate a single outline (for concurrent execution)"""
        result = {
            'topic': topic,
            'category': category,
            'status': 'skipped',
            'error': None
        }
        
        try:
            # Check if outline already exists
            outline_path = self.get_outline_path(topic, category)
            if outline_path.exists() and not self.force_regenerate:
                self.safe_print(f"  ✓ Outline already exists: {topic}")
                return result
            
            # Generate outline with rate limiting
            self.safe_print(f"  → Generating outline: {topic}")
            outline = self.rate_limited_api_call(self.generate_article_outline, topic, category)
            
            # Save outline
            self.save_outline(topic, category, outline)
            result['status'] = 'generated'
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            self.safe_print(f"  ❌ ERROR generating outline {topic}: {str(e)}")
        
        return result
    
    def generate_all_outlines(self) -> None:
        """Phase 1: Generate all outlines concurrently"""
        self.safe_print("\n📋 Phase 1: Generating all outlines concurrently...")
        
        # Collect all topics to process
        all_topics = []
        for category, topics in self.categories.items():
            for topic in topics:
                all_topics.append((topic, category))
        
        self.safe_print(f"Processing {len(all_topics)} topics with {self.max_concurrent} concurrent workers...")
        
        outline_count = 0
        skipped_count = 0
        error_count = 0
        
        # Process topics concurrently
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # Submit all tasks
            future_to_topic = {
                executor.submit(self.generate_single_outline, topic, category): (topic, category)
                for topic, category in all_topics
            }
            
            # Process completed tasks
            for future in as_completed(future_to_topic):
                topic, category = future_to_topic[future]
                try:
                    result = future.result()
                    
                    with self.stats_lock:
                        if result['status'] == 'generated':
                            outline_count += 1
                        elif result['status'] == 'skipped':
                            skipped_count += 1
                        elif result['status'] == 'error':
                            error_count += 1
                            
                except Exception as e:
                    self.safe_print(f"  ❌ Unexpected error for {topic}: {str(e)}")
                    with self.stats_lock:
                        error_count += 1
        
        self.safe_print(f"\n✅ Outline Generation Summary:")
        self.safe_print(f"  - Generated: {outline_count} outlines")
        self.safe_print(f"  - Skipped: {skipped_count} existing outlines")
        self.safe_print(f"  - Errors: {error_count} failed outlines")
    
    def generate_single_content(self, topic: str, category: str) -> Dict:
        """Generate content and images for a single topic (for concurrent execution)"""
        result = {
            'topic': topic,
            'category': category,
            'article_status': 'skipped',
            'images_generated': 0,
            'article_data': None,
            'error': None
        }
        
        try:
            # Load outline
            outline = self.load_outline(topic, category)
            if not outline:
                result['error'] = f"No outline found for: {topic}"
                self.safe_print(f"  ❌ No outline found for: {topic}")
                return result
            
            # Check if article already exists
            article_path = Path("content") / f"{topic}.md"
            article_exists = article_path.exists()
            
            if article_exists and not self.force_regenerate:
                self.safe_print(f"  ✓ Article already exists: {topic}")
                
                # Extract existing article metadata for index
                try:
                    with open(article_path, 'r') as f:
                        content = f.read()
                        # Extract title from frontmatter
                        title_line = [line for line in content.split('\n') if line.startswith('title:')][0]
                        title = title_line.split('"')[1]
                        
                        # Extract keywords from content
                        keywords_line = [line for line in content.split('\n') if line.startswith('keywords:')][0]
                        keywords = [k.strip() for k in keywords_line.split('"')[1].split(',')]
                        
                        result['article_data'] = {
                            "topic": topic,
                            "category": category,
                            "title": title,
                            "keywords": keywords
                        }
                except:
                    # Fallback to outline data if parsing fails
                    result['article_data'] = {
                        "topic": topic,
                        "category": category,
                        "title": outline['title'],
                        "keywords": outline['keywords']
                    }
            else:
                # Generate new article content with rate limiting
                self.safe_print(f"  → Generating content: {topic}")
                content = self.rate_limited_api_call(self.generate_article_content, topic, category, outline)
                
                # Create/update article file
                self.safe_print(f"  → Creating article: {topic}")
                self.create_article_file_only(topic, category, content, outline)
                
                result['article_data'] = {
                    "topic": topic,
                    "category": category,
                    "title": outline['title'],
                    "keywords": outline['keywords']
                }
                result['article_status'] = 'generated'
            
            # Check and generate missing images
            self.safe_print(f"  → Checking/generating images: {topic}")
            missing_images = self.check_missing_images(category, outline)
            if missing_images:
                self.safe_print(f"    Found {len(missing_images)} missing images for {topic}")
                result['images_generated'] = self.generate_images_from_outline(topic, category, outline)
            else:
                self.safe_print(f"    All images already exist for {topic}")
                
        except Exception as e:
            result['error'] = str(e)
            self.safe_print(f"  ❌ ERROR generating content for {topic}: {str(e)}")
        
        return result
    
    def generate_all_content(self) -> List[Dict]:
        """Phase 2: Generate content and images concurrently"""
        self.safe_print("\n📝 Phase 2: Generating content and images concurrently...")
        
        # Collect all topics to process
        all_topics = []
        for category, topics in self.categories.items():
            for topic in topics:
                all_topics.append((topic, category))
        
        self.safe_print(f"Processing {len(all_topics)} topics with {self.max_concurrent} concurrent workers...")
        
        all_articles = []
        skipped_count = 0
        generated_count = 0
        image_count = 0
        error_count = 0
        
        # Process topics concurrently
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # Submit all tasks
            future_to_topic = {
                executor.submit(self.generate_single_content, topic, category): (topic, category)
                for topic, category in all_topics
            }
            
            # Process completed tasks
            for future in as_completed(future_to_topic):
                topic, category = future_to_topic[future]
                try:
                    result = future.result()
                    
                    with self.stats_lock:
                        if result['article_data']:
                            all_articles.append(result['article_data'])
                        
                        if result['article_status'] == 'generated':
                            generated_count += 1
                        elif result['article_status'] == 'skipped':
                            skipped_count += 1
                        
                        image_count += result['images_generated']
                        
                        if result['error']:
                            error_count += 1
                            
                except Exception as e:
                    self.safe_print(f"  ❌ Unexpected error for {topic}: {str(e)}")
                    with self.stats_lock:
                        error_count += 1
        
        # Save article index for reference
        with open("article_index.json", "w") as f:
            json.dump(all_articles, f, indent=2)
        
        self.safe_print(f"\n✅ Content Generation Summary:")
        self.safe_print(f"  - Generated: {generated_count} articles")
        self.safe_print(f"  - Skipped: {skipped_count} existing articles")
        self.safe_print(f"  - Images generated: {image_count} images")
        self.safe_print(f"  - Errors: {error_count} failed topics")
        self.safe_print(f"  - Total indexed: {len(all_articles)} articles")
        
        return all_articles
    
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
        """Generate all articles using two-phase concurrent approach"""
        self.safe_print("MagicLookBook.com Article Generator - Two-Phase Concurrent Approach")
        self.safe_print("=" * 70)
        self.safe_print(f"Concurrency: {self.max_concurrent} workers")
        
        # Phase 1: Generate all outlines
        self.generate_all_outlines()
        
        # Cross-reference analysis
        self.analyze_cross_references()
        
        # Phase 2: Generate content and images
        articles = self.generate_all_content()
        
        # Update cross-references
        self.update_cross_references()
        
        self.safe_print("\n✅ Two-Phase Concurrent Generation Complete!")
        return articles
    
    def update_cross_references(self):
        """Update articles to reference each other properly"""
        self.safe_print("\nUpdating cross-references between articles...")
        
        # This would scan all articles and update the [[Article Name]] references
        # to proper markdown links based on the actual file names
        
        content_dir = Path("content")
        for md_file in content_dir.glob("*.md"):
            content = md_file.read_text()
            
            # Simple replacement of [[Title]] with [Title](/content/topic-name/)
            # In production, you'd want more sophisticated matching
            
            # For now, just print what would be updated
            if "[[" in content:
                self.safe_print(f"  Would update references in: {md_file.name}")

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
    parser.add_argument(
        "--concurrent",
        type=int,
        default=5,
        help="Number of concurrent workers (default: 5, recommended: 3-8 for API stability)"
    )
    
    args = parser.parse_args()
    
    print("MagicLookBook.com Article Generator")
    print("=" * 40)
    
    if args.all:
        print("🔄 Force regeneration mode: ON")
    
    # Warn about high concurrency
    if args.concurrent > 8:
        print(f"⚠️  WARNING: High concurrency ({args.concurrent}) may cause API rate limiting issues")
        print("   Consider using --concurrent 3-5 for better stability")
    
    # Create generator instance
    generator = ArticleGenerator(force_regenerate=args.all, max_concurrent=args.concurrent)
    
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
