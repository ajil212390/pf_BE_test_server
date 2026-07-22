using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ProductCatalogApi.Data;
using ProductCatalogApi.Models;

namespace ProductCatalogApi.Controllers
{
    [ApiController]
    [Route("")]
    public class AuthController : ControllerBase
    {
        private readonly AppDbContext _context;

        public AuthController(AppDbContext context)
        {
            _context = context;
        }

        [HttpPost("register")]
        public async Task<IActionResult> RegisterUser([FromBody] RegisterDto data)
        {
            try
            {
                Company? company = null;
                if (!string.IsNullOrEmpty(data.CompanyName))
                {
                    company = await _context.Companies.FirstOrDefaultAsync(c => c.CompanyName == data.CompanyName);
                    if (company == null)
                    {
                        company = new Company
                        {
                            CompanyName = data.CompanyName,
                            CompanyPhoneNumber = data.CompanyPhoneNumber
                        };
                        _context.Companies.Add(company);
                        await _context.SaveChangesAsync();
                    }
                }

                var user = new User
                {
                    Username = data.Username,
                    UserEmail = data.UserEmail,
                    UserPassword = data.UserPassword,
                    CompanyId = company?.CompanyId
                };

                _context.Users.Add(user);
                await _context.SaveChangesAsync();

                return Created("", new
                {
                    message = "Registration successful",
                    userid = user.UserId,
                    username = user.Username,
                    companyid = company?.CompanyId
                });
            }
            catch (Exception ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }

        [HttpPost("login")]
        public async Task<IActionResult> LoginUser([FromBody] LoginDto data)
        {
            try
            {
                var user = await _context.Users
                    .Include(u => u.Company)
                    .FirstOrDefaultAsync(u => u.Username != null && u.Username.ToLower() == data.Username.ToLower());

                if (user != null)
                {
                    if (user.UserPassword == data.UserPassword)
                    {
                        return Ok(new
                        {
                            message = "Login successful",
                            userid = user.UserId,
                            username = user.Username,
                            useremail = user.UserEmail ?? "",
                            companyid = user.CompanyId,
                            companyname = user.Company?.CompanyName ?? "",
                            companyphonenumber = user.Company?.CompanyPhoneNumber?.ToString() ?? ""
                        });
                    }
                    else
                    {
                        return Unauthorized(new { error = "Incorrect password." });
                    }
                }
                return NotFound(new { error = "Username not found." });
            }
            catch (Exception ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }

        [HttpPost("update-company")]
        public async Task<IActionResult> UpdateCompany([FromBody] UpdateCompanyDto data)
        {
            try
            {
                var user = await _context.Users
                    .Include(u => u.Company)
                    .FirstOrDefaultAsync(u => u.UserId == data.UserId);

                if (user == null)
                    return NotFound(new { error = "User not found" });

                var company = user.Company;
                if (company != null)
                {
                    if (!string.IsNullOrEmpty(data.CompanyName))
                        company.CompanyName = data.CompanyName;
                    if (data.CompanyPhoneNumber.HasValue)
                        company.CompanyPhoneNumber = data.CompanyPhoneNumber;

                    await _context.SaveChangesAsync();
                    return Ok(new { message = "Company updated successfully" });
                }

                return NotFound(new { error = "No company found for this user" });
            }
            catch (Exception ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }

        [HttpPost("change-password")]
        public async Task<IActionResult> ChangePassword([FromBody] ChangePasswordDto data)
        {
            try
            {
                var user = await _context.Users.FirstOrDefaultAsync(u => u.UserId == data.UserId);
                if (user == null)
                    return NotFound(new { error = "User not found." });

                if (user.UserPassword != data.CurrentPassword)
                    return BadRequest(new { error = "Incorrect current password." });

                user.UserPassword = data.NewPassword;
                await _context.SaveChangesAsync();
                return Ok(new { message = "Password changed successfully." });
            }
            catch (Exception ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }
    }

    public class RegisterDto
    {
        public string? CompanyName { get; set; }
        public long? CompanyPhoneNumber { get; set; }
        public string? Username { get; set; }
        public string? UserEmail { get; set; }
        public string? UserPassword { get; set; }
    }

    public class LoginDto
    {
        public string Username { get; set; } = string.Empty;
        public string UserPassword { get; set; } = string.Empty;
    }

    public class UpdateCompanyDto
    {
        public int UserId { get; set; }
        public string? CompanyName { get; set; }
        public long? CompanyPhoneNumber { get; set; }
    }

    public class ChangePasswordDto
    {
        public int UserId { get; set; }
        public string? CurrentPassword { get; set; }
        public string? NewPassword { get; set; }
    }
}
