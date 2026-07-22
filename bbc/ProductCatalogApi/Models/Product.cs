using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace ProductCatalogApi.Models
{
    [Table("products")]
    public class Product
    {
        [Key]
        [Column("productid")]
        public int ProductId { get; set; }

        [Column("productname")]
        [MaxLength(150)]
        public string? ProductName { get; set; }

        [Column("productcategoryid")]
        public int? ProductCategoryId { get; set; }

        [ForeignKey("ProductCategoryId")]
        public ProductCategory? ProductCategory { get; set; }

        [Column("productunitid")]
        public int? ProductUnitId { get; set; }

        [ForeignKey("ProductUnitId")]
        public ProductUnit? ProductUnit { get; set; }

        [Column("productprice")]
        public decimal ProductPrice { get; set; }

        [Column("productphotopath")]
        [MaxLength(2000)]
        public string? ProductPhotoPath { get; set; }

        [Column("dateadded")]
        public DateTime? DateAdded { get; set; }

        [Column("userid")]
        public int? UserId { get; set; }

        [ForeignKey("UserId")]
        public User? User { get; set; }

        [Column("companyid")]
        public int? CompanyId { get; set; }

        [ForeignKey("CompanyId")]
        public Company? Company { get; set; }

        [Column("createdat")]
        public DateTime? CreatedAt { get; set; }

        [Column("addtype")]
        [MaxLength(10)]
        public string? AddType { get; set; }
    }
}
