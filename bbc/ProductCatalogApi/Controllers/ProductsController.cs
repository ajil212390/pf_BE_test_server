using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ProductCatalogApi.Data;
using ProductCatalogApi.Models;
using System.Globalization;

namespace ProductCatalogApi.Controllers
{
    public class ProductFormDto
    {
        public string? productname { get; set; }
        public decimal? productprice { get; set; }
        public int? productcategoryid { get; set; }
        public int? productunitid { get; set; }
        public int? userid { get; set; }
        public string? dateadded { get; set; }
        public string? retained_images { get; set; }
        public List<IFormFile>? files { get; set; }
    }

    [ApiController]
    [Route("products")]
    public class ProductsController : ControllerBase
    {
        private readonly AppDbContext _context;
        private readonly IConfiguration _configuration;
        private readonly string _mediaRoot;

        public ProductsController(AppDbContext context, IConfiguration configuration)
        {
            _context = context;
            _configuration = configuration;
            _mediaRoot = _configuration.GetValue<string>("MediaRoot") ?? @"D:\Products";
            System.Text.Encoding.RegisterProvider(System.Text.CodePagesEncodingProvider.Instance);
        }

        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var products = await _context.Products
                .Include(p => p.ProductCategory)
                .Include(p => p.ProductUnit)
                .Include(p => p.Company)
                .ToListAsync();

            var request = HttpContext.Request;
            var baseUrl = $"{request.Scheme}://{request.Host}{request.PathBase}/media/";

            var result = products.Select(p => new
            {
                p.ProductId,
                p.ProductName,
                p.ProductCategoryId,
                p.ProductUnitId,
                p.ProductPrice,
                p.ProductPhotoPath,
                p.DateAdded,
                p.UserId,
                p.CompanyId,
                p.CreatedAt,
                p.AddType,
                categoryname = p.ProductCategory?.ProductCategoryName,
                unitname = p.ProductUnit?.ProductUnitName,
                companyname = p.Company?.CompanyName,
                productphotourl = GetPhotoUrls(p.ProductPhotoPath, baseUrl)
            });

            return Ok(result);
        }

        [HttpGet("{id}")]
        public async Task<IActionResult> GetById(int id)
        {
            var p = await _context.Products
                .Include(pr => pr.ProductCategory)
                .Include(pr => pr.ProductUnit)
                .Include(pr => pr.Company)
                .FirstOrDefaultAsync(pr => pr.ProductId == id);

            if (p == null) return NotFound();

            var request = HttpContext.Request;
            var baseUrl = $"{request.Scheme}://{request.Host}{request.PathBase}/media/";

            var result = new
            {
                p.ProductId,
                p.ProductName,
                p.ProductCategoryId,
                p.ProductUnitId,
                p.ProductPrice,
                p.ProductPhotoPath,
                p.DateAdded,
                p.UserId,
                p.CompanyId,
                p.CreatedAt,
                p.AddType,
                categoryname = p.ProductCategory?.ProductCategoryName,
                unitname = p.ProductUnit?.ProductUnitName,
                companyname = p.Company?.CompanyName,
                productphotourl = GetPhotoUrls(p.ProductPhotoPath, baseUrl)
            };

            return Ok(result);
        }

        private List<string> GetPhotoUrls(string? paths, string baseUrl)
        {
            if (string.IsNullOrEmpty(paths)) return new List<string>();
            var pathArray = paths.Split(',');
            var urls = new List<string>();
            foreach (var path in pathArray)
            {
                var cleanPath = path.Trim();
                if (string.IsNullOrEmpty(cleanPath)) continue;
                
                // Convert Windows backslashes to forward slashes for URLs
                cleanPath = cleanPath.Replace('\\', '/');
                
                urls.Add($"{baseUrl}{cleanPath}");
            }
            return urls;
        }

        [HttpPost]
        [Consumes("multipart/form-data")]
        public async Task<IActionResult> Post([FromForm] ProductFormDto data)
        {
            var product = new Product
            {
                ProductName = data.productname,
                AddType = "Single",
                DateAdded = DateTime.TryParse(data.dateadded, out var date) ? date.ToUniversalTime() : null,
                CreatedAt = DateTime.UtcNow
            };

            if (data.productprice.HasValue) product.ProductPrice = data.productprice.Value;
            if (data.productcategoryid.HasValue) product.ProductCategoryId = data.productcategoryid.Value;
            if (data.productunitid.HasValue) product.ProductUnitId = data.productunitid.Value;
            
            if (data.userid.HasValue)
            {
                product.UserId = data.userid.Value;
                var user = await _context.Users.FindAsync(data.userid.Value);
                if (user != null && user.CompanyId.HasValue)
                {
                    product.CompanyId = user.CompanyId;
                }
            }
            
            var savedPaths = new List<string>();
            if (data.files != null || data.retained_images != null)
            {
                savedPaths = await HandleImageUploads(data.files, data.retained_images);
            }
            product.ProductPhotoPath = string.Join(",", savedPaths);

            _context.Products.Add(product);
            await _context.SaveChangesAsync();

            return CreatedAtAction(nameof(GetById), new { id = product.ProductId }, product);
        }

        [HttpPut("{id}")]
        [Consumes("multipart/form-data")]
        public async Task<IActionResult> Put(int id, [FromForm] ProductFormDto data)
        {
            var product = await _context.Products.FindAsync(id);
            if (product == null) return NotFound();

            if (!string.IsNullOrEmpty(data.productname)) product.ProductName = data.productname;
            if (data.productprice.HasValue) product.ProductPrice = data.productprice.Value;
            if (data.productcategoryid.HasValue) product.ProductCategoryId = data.productcategoryid.Value;
            if (data.productunitid.HasValue) product.ProductUnitId = data.productunitid.Value;
            if (!string.IsNullOrEmpty(data.dateadded) && DateTime.TryParse(data.dateadded, out var date)) product.DateAdded = date.ToUniversalTime();

            bool isImageUpdate = (data.files != null && data.files.Any()) || Request.Form.ContainsKey("retained_images");
            if (isImageUpdate)
            {
                var savedPaths = await HandleImageUploads(data.files, data.retained_images);
                product.ProductPhotoPath = string.Join(",", savedPaths);
            }

            await _context.SaveChangesAsync();
            return Ok(product);
        }
        
        [HttpPatch("{id}")]
        public async Task<IActionResult> Patch(int id, [FromBody] Product patchData)
        {
            var product = await _context.Products.FindAsync(id);
            if (product == null) return NotFound();
            
            if (!string.IsNullOrEmpty(patchData.ProductName)) product.ProductName = patchData.ProductName;
            if (patchData.ProductPrice != 0) product.ProductPrice = patchData.ProductPrice;
            if (patchData.ProductCategoryId.HasValue) product.ProductCategoryId = patchData.ProductCategoryId;
            if (patchData.ProductUnitId.HasValue) product.ProductUnitId = patchData.ProductUnitId;
            
            await _context.SaveChangesAsync();
            return Ok(product);
        }

        [HttpDelete("{id}")]
        public async Task<IActionResult> Delete(int id)
        {
            var product = await _context.Products.FindAsync(id);
            if (product == null) return NotFound();

            _context.Products.Remove(product);
            await _context.SaveChangesAsync();
            return NoContent();
        }

        private async Task<List<string>> HandleImageUploads(List<IFormFile>? files, string? retainedImages)
        {
            var savedPaths = new List<string>();
            if (!string.IsNullOrEmpty(retainedImages))
            {
                savedPaths.AddRange(retainedImages.Split(',').Select(i => i.Trim()).Where(i => !string.IsNullOrEmpty(i)));
            }

            if (files == null) return savedPaths;

            var productsFolder = Path.Combine(_mediaRoot, "products");
            if (!Directory.Exists(productsFolder))
            {
                Directory.CreateDirectory(productsFolder);
            }

            foreach (var file in files)
            {
                // Accept any file name or limit to "productphotopath" or "files" 
                // Currently the frontend might send them as "files" instead of "productphotopath".
                var filename = $"scaled_{Guid.NewGuid().ToString("N")}_{file.FileName}";
                var path = Path.Combine(productsFolder, filename);
                
                using (var stream = new FileStream(path, FileMode.Create))
                {
                    await file.CopyToAsync(stream);
                }
                savedPaths.Add($"products/{filename}");
            }

            return savedPaths;
        }
    }
}
