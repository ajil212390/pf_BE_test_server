import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import SupplierExecutive, ExecutiveAllocation, Company

def sync():
    allocations_map = {
        1: [1, 2, 3],  # abcexe -> AN Gallery, Navas Bakers, AI Supermart
        2: [3, 6, 4],  # keralaexe -> AI Supermart, Calvino Mart, Western Mart
        3: [2, 3, 4],  # malabarexe -> Navas Bakers, AI Supermart, Western Mart
        4: [4, 2, 1],  # metroexe -> Western Mart, Navas Bakers, AN Gallery
        5: [6, 3, 1],  # greenexe -> Calvino Mart, AI Supermart, AN Gallery
    }
    
    count = 0
    for exe_id, comp_ids in allocations_map.items():
        exe = SupplierExecutive.objects.get(executiveid=exe_id)
        for cid in comp_ids:
            comp = Company.objects.get(companyid=cid)
            alloc, created = ExecutiveAllocation.objects.get_or_create(executive=exe, company=comp)
            if created:
                count += 1
                print(f"  + Allocated Executive '{exe.executive_name}' (ID #{exe.executiveid}) -> Store: {comp.companyname} (ID #{comp.companyid})")

    print(f"Total new executive allocations added: {count}")

if __name__ == '__main__':
    sync()
