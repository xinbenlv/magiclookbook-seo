export default function (eleventyConfig) {
  // Set input directory to current directory
  eleventyConfig.setInputDirectory(".");
  
  // Set output directory
  eleventyConfig.setOutputDirectory("_site");

  // Ignore specific files that should not be processed
  eleventyConfig.ignores.add("README.md");
  eleventyConfig.ignores.add("plan.md");
  eleventyConfig.ignores.add("instruction.md");
  eleventyConfig.ignores.add("package.json");
  eleventyConfig.ignores.add("package-lock.json");
  eleventyConfig.ignores.add("eleventy.config.js");
  
  // Copy images from content/images directory
  eleventyConfig.addPassthroughCopy("content/images");
  
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
    templateFormats: ["md", "html"]
  };
};
