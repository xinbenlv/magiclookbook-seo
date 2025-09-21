import sitemap from "@quasibit/eleventy-plugin-sitemap";

export default function (eleventyConfig) {
  // Set input directory to current directory
  eleventyConfig.setInputDirectory(".");
  
  // Set output directory
  eleventyConfig.setOutputDirectory("_site");
  
  // Add sitemap plugin
  eleventyConfig.addPlugin(sitemap, {
    sitemap: {
      hostname: "https://content.magiclookbook.com", // Replace with your actual domain
      lastModifiedProperty: "modified",
      changefreq: "weekly",
      priority: 0.8
    }
  });

  // Ignore specific files that should not be processed
  eleventyConfig.ignores.add("README.md");
  eleventyConfig.ignores.add("plan.md");
  eleventyConfig.ignores.add("instruction.md");
  eleventyConfig.ignores.add("package.json");
  eleventyConfig.ignores.add("package-lock.json");
  eleventyConfig.ignores.add("eleventy.config.js");
  
  // Copy images from content/images directory
  eleventyConfig.addPassthroughCopy("content/images");
  
  // Copy CSS files
  eleventyConfig.addPassthroughCopy("css");
  
  // Copy JavaScript files
  eleventyConfig.addPassthroughCopy("js");
  
  // Copy robots.txt
  eleventyConfig.addPassthroughCopy("robots.txt");
  
  // Add date filter for sitemap
  eleventyConfig.addFilter("dateToISO", (date) => {
    return new Date(date).toISOString();
  });
  
  // Alternative: if you want more control over specific image types
  // eleventyConfig.addPassthroughCopy("content/images/**/*.png");
  // eleventyConfig.addPassthroughCopy("content/images/**/*.jpg");
  // eleventyConfig.addPassthroughCopy("content/images/**/*.jpeg");
  // eleventyConfig.addPassthroughCopy("content/images/**/*.gif");
  // eleventyConfig.addPassthroughCopy("content/images/**/*.svg");

  return {
    dir: {
      input: ".",
      output: "_site",
      includes: "_includes",
      data: "_data"
    },
    // Only process markdown and html files
    templateFormats: ["md", "html", "njk"]
  };
};
