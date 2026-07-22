using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace ProductCatalogApi.Models
{
    [Table("company")]
    public class Company
    {
        [Key]
        [Column("companyid")]
        public int CompanyId { get; set; }

        [Column("companyname")]
        [MaxLength(200)]
        public string? CompanyName { get; set; }

        [Column("companyphonenumber")]
        public long? CompanyPhoneNumber { get; set; }
    }
}
