using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ProductCatalogApi.Data;

namespace ProductCatalogApi.Controllers
{
    [ApiController]
    [Route("admin")]
    public class AdminController : ControllerBase
    {
        private readonly AppDbContext _context;
        private const string ADMIN_USERNAME = "admin";
        private const string ADMIN_COMPANY = "Admin HQ";

        public AdminController(AppDbContext context)
        {
            _context = context;
        }

        [HttpGet("overview")]
        public async Task<IActionResult> GetOverview()
        {
            var totalCompanies = await _context.Companies
                .Where(c => c.CompanyName != null && c.CompanyName.ToLower() != ADMIN_COMPANY.ToLower())
                .CountAsync();

            var totalUsers = await _context.Users
                .Where(u => u.Username != null && u.Username.ToLower() != ADMIN_USERNAME.ToLower())
                .CountAsync();

            var totalProducts = await _context.Products.CountAsync();

            return Ok(new
            {
                total_companies = totalCompanies,
                total_users = totalUsers,
                total_products = totalProducts
            });
        }

        [HttpGet("companies")]
        public async Task<IActionResult> GetCompanies()
        {
            var companies = await _context.Companies
                .Where(c => c.CompanyName != null && c.CompanyName.ToLower() != ADMIN_COMPANY.ToLower())
                .ToListAsync();

            var result = new List<object>();
            foreach (var c in companies)
            {
                var userCount = await _context.Users
                    .Where(u => u.CompanyId == c.CompanyId && u.Username != null && u.Username.ToLower() != ADMIN_USERNAME.ToLower())
                    .CountAsync();
                
                var productCount = await _context.Products
                    .Where(p => p.CompanyId == c.CompanyId)
                    .CountAsync();

                result.Add(new
                {
                    companyid = c.CompanyId,
                    companyname = c.CompanyName,
                    companyphonenumber = c.CompanyPhoneNumber?.ToString() ?? "",
                    user_count = userCount,
                    product_count = productCount
                });
            }

            return Ok(result);
        }

        [HttpGet("users")]
        public async Task<IActionResult> GetUsers()
        {
            var users = await _context.Users
                .Include(u => u.Company)
                .Where(u => u.Username != null && u.Username.ToLower() != ADMIN_USERNAME.ToLower())
                .ToListAsync();

            var result = new List<object>();
            foreach (var u in users)
            {
                var productCount = await _context.Products
                    .Where(p => p.UserId == u.UserId)
                    .CountAsync();

                result.Add(new
                {
                    userid = u.UserId,
                    username = u.Username,
                    useremail = u.UserEmail ?? "",
                    companyname = u.Company?.CompanyName ?? "No Company",
                    product_count = productCount
                });
            }
            return Ok(result);
        }

        [HttpGet("products")]
        public async Task<IActionResult> GetProducts()
        {
            var products = await _context.Products
                .Include(p => p.User)
                .Include(p => p.Company)
                .Include(p => p.ProductCategory)
                .Include(p => p.ProductUnit)
                .OrderByDescending(p => p.ProductId)
                .ToListAsync();

            var request = HttpContext.Request;
            var baseUrl = $"{request.Scheme}://{request.Host}{request.PathBase}/media/";

            var result = products.Select(p => new
            {
                productid = p.ProductId,
                productname = p.ProductName,
                productprice = p.ProductPrice.ToString(),
                category = p.ProductCategory?.ProductCategoryName ?? "",
                unit = p.ProductUnit?.ProductUnitName ?? "",
                dateadded = p.DateAdded?.ToString("yyyy-MM-dd") ?? "",
                createdat = p.CreatedAt?.ToString("yyyy-MM-dd HH:mm") ?? "",
                addtype = p.AddType ?? "Single",
                uploaded_by = p.User?.Username ?? "Unknown",
                userid = p.UserId,
                company = p.Company?.CompanyName ?? "No Company",
                productphotourl = GetPhotoUrls(p.ProductPhotoPath, baseUrl)
            });

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

        [HttpGet("user/{userId}/products")]
        public async Task<IActionResult> GetUserProducts(int userId)
        {
            var user = await _context.Users
                .Include(u => u.Company)
                .FirstOrDefaultAsync(u => u.UserId == userId);

            if (user == null)
                return NotFound(new { error = "User not found" });

            var products = await _context.Products
                .Include(p => p.ProductCategory)
                .Include(p => p.ProductUnit)
                .Where(p => p.UserId == userId)
                .OrderByDescending(p => p.CreatedAt)
                .ThenByDescending(p => p.ProductId)
                .ToListAsync();

            var request = HttpContext.Request;
            var baseUrl = $"{request.Scheme}://{request.Host}{request.PathBase}/media/";

            var result = products.Select(p => new
            {
                productid = p.ProductId,
                productname = p.ProductName,
                productprice = p.ProductPrice.ToString(),
                category = p.ProductCategory?.ProductCategoryName ?? "",
                unit = p.ProductUnit?.ProductUnitName ?? "",
                dateadded = p.DateAdded?.ToString("yyyy-MM-dd") ?? "",
                createdat = p.CreatedAt?.ToString("yyyy-MM-dd HH:mm") ?? "",
                addtype = p.AddType ?? "Single",
                productphotourl = GetPhotoUrls(p.ProductPhotoPath, baseUrl)
            }).ToList();

            return Ok(new
            {
                username = user.Username,
                useremail = user.UserEmail ?? "",
                company = user.Company?.CompanyName ?? "",
                total = result.Count,
                products = result
            });
        }

        [HttpGet("company/{companyId}/products")]
        public async Task<IActionResult> GetCompanyProducts(int companyId)
        {
            var company = await _context.Companies.FirstOrDefaultAsync(c => c.CompanyId == companyId);
            if (company == null)
                return NotFound(new { error = "Company not found" });

            var products = await _context.Products
                .Include(p => p.ProductCategory)
                .Include(p => p.ProductUnit)
                .Where(p => p.CompanyId == companyId)
                .OrderByDescending(p => p.CreatedAt)
                .ThenByDescending(p => p.ProductId)
                .ToListAsync();

            var result = products.Select(p => new
            {
                productid = p.ProductId,
                productname = p.ProductName,
                productprice = p.ProductPrice.ToString(),
                category = p.ProductCategory?.ProductCategoryName ?? "",
                unit = p.ProductUnit?.ProductUnitName ?? "",
                dateadded = p.DateAdded?.ToString("yyyy-MM-dd") ?? "",
                createdat = p.CreatedAt?.ToString("yyyy-MM-dd HH:mm") ?? "",
                addtype = p.AddType ?? "Single"
            }).ToList();

            return Ok(new
            {
                companyname = company.CompanyName,
                companyphone = company.CompanyPhoneNumber?.ToString() ?? "",
                total = result.Count,
                products = result
            });
        }
    }
}
