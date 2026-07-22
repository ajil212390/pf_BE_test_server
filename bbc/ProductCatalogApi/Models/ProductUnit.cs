using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace ProductCatalogApi.Models
{
    [Table("productunit")]
    public class ProductUnit
    {
        [Key]
        [Column("productunitid")]
        public int ProductUnitId { get; set; }

        [Column("productunitname")]
        [MaxLength(50)]
        public string? ProductUnitName { get; set; }
    }
}
