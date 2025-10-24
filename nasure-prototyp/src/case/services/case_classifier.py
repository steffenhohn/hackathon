# from uuid import uuid4
# from case.domain.domain import CaseRecord
# from case.adapters.repository import AbstractRepository
# from typing import Tuple    

# class CaseMgmtService:
#     def __init__(self, repo: AbstractRepository):
#         self.repo = repo
        
#     def create_case(self, patient_id: str, case_date: str, case_class: str, 
#                    case_status: str, pathogen: str, canton: str) -> Tuple[str, bool]:
#         """
#         Create a new case record.
        
#         Returns:
#             Tuple of (case_id, created)
#         """
#         # Generate new case ID
#         case_id = str(uuid4())
        
#         # Create case record
#         new_case = CaseRecord(
#             case_id=case_id,
#             patient_id=patient_id,
#             case_date=case_date,
#             case_class=case_class,
#             case_status=case_status,
#             pathogen=pathogen,
#             canton=canton
#         )
        
#         # Save to repository
#         created_case = self.repo.add(new_case)
        
#         if created_case:
#             return case_id, True
#         else:
#             return case_id, False