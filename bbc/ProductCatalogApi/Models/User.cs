using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace ProductCatalogApi.Models
{
    [Table("users")]
    public class User
    {
        [Key]
        [Column("userid")]
        public int UserId { get; set; }

        [Column("username")]
        [MaxLength(120)]
        public string? Username { get; set; }

        [Column("useremail")]
        [MaxLength(200)]
        public string? UserEmail { get; set; }

        [Column("userpassword")]
        [MaxLength(120)]
        public string? UserPassword { get; set; }

        [Column("companyid")]
        public int? CompanyId { get; set; }

        [ForeignKey("CompanyId")]
        public Company? Company { get; set; }
    }
}
