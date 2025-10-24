import { Component, OnInit, ViewChild } from '@angular/core';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { DiseaseReportService } from '../services/disease-report.service';
import { DiseaseReport } from '../models/disease-report.model';

@Component({
  selector: 'app-disease-report-table',
  templateUrl: './disease-report-table.component.html',
  styleUrls: ['./disease-report-table.component.scss']
})
export class DiseaseReportTableComponent implements OnInit {
  displayedColumns: string[] = ['id', 'disease', 'location', 'date', 'status'];
  dataSource = new MatTableDataSource<DiseaseReport>();

  @ViewChild(MatPaginator, { static: true }) paginator!: MatPaginator;
  @ViewChild(MatSort, { static: true }) sort!: MatSort;

   // Static data for testing
     private staticData: DiseaseReport[] = [
       { id: 1, disease: 'Influenza', location: 'Berlin', date: '2025-10-20', status: 'Aktiv' },
       { id: 2, disease: 'COVID-19', location: 'München', date: '2025-10-18', status: 'Behandelt' },
       { id: 3, disease: 'Masern', location: 'Hamburg', date: '2025-10-15', status: 'Aktiv' },
       { id: 4, disease: 'Tuberkulose', location: 'Köln', date: '2025-10-12', status: 'Unter Beobachtung' },
       { id: 5, disease: 'Hepatitis A', location: 'Frankfurt', date: '2025-10-10', status: 'Geheilt' },
       { id: 6, disease: 'Salmonellose', location: 'Stuttgart', date: '2025-10-09', status: 'Aktiv' },
       { id: 7, disease: 'Norovirus', location: 'Düsseldorf', date: '2025-10-08', status: 'Behandelt' },
       { id: 8, disease: 'Windpocken', location: 'Dortmund', date: '2025-10-07', status: 'Aktiv' },
       { id: 9, disease: 'Röteln', location: 'Essen', date: '2025-10-06', status: 'Geheilt' },
       { id: 10, disease: 'Mumps', location: 'Leipzig', date: '2025-10-05', status: 'Unter Beobachtung' },
       { id: 11, disease: 'Hepatitis B', location: 'Bremen', date: '2025-10-04', status: 'Aktiv' },
       { id: 12, disease: 'Meningitis', location: 'Dresden', date: '2025-10-03', status: 'Behandelt' },
       { id: 13, disease: 'Legionellose', location: 'Hannover', date: '2025-10-02', status: 'Aktiv' },
       { id: 14, disease: 'Tetanus', location: 'Nürnberg', date: '2025-10-01', status: 'Geheilt' },
       { id: 15, disease: 'Keuchhusten', location: 'Duisburg', date: '2025-09-30', status: 'Unter Beobachtung' },
       { id: 16, disease: 'Scharlach', location: 'Bochum', date: '2025-09-29', status: 'Aktiv' },
       { id: 17, disease: 'EHEC', location: 'Wuppertal', date: '2025-09-28', status: 'Behandelt' },
       { id: 18, disease: 'Listeriose', location: 'Bonn', date: '2025-09-27', status: 'Aktiv' },
       { id: 19, disease: 'Typhus', location: 'Bielefeld', date: '2025-09-26', status: 'Geheilt' },
       { id: 20, disease: 'Malaria', location: 'Mannheim', date: '2025-09-25', status: 'Unter Beobachtung' },
       { id: 21, disease: 'Dengue-Fieber', location: 'Karlsruhe', date: '2025-09-24', status: 'Aktiv' },
       { id: 22, disease: 'Cholera', location: 'Münster', date: '2025-09-23', status: 'Behandelt' },
       { id: 23, disease: 'Ebola', location: 'Augsburg', date: '2025-09-22', status: 'Aktiv' },
       { id: 24, disease: 'Zika-Virus', location: 'Wiesbaden', date: '2025-09-21', status: 'Geheilt' },
       { id: 25, disease: 'Gelbfieber', location: 'Gelsenkirchen', date: '2025-09-20', status: 'Unter Beobachtung' },
       { id: 26, disease: 'Tollwut', location: 'Mönchengladbach', date: '2025-09-19', status: 'Aktiv' },
       { id: 27, disease: 'Borreliose', location: 'Braunschweig', date: '2025-09-18', status: 'Behandelt' },
       { id: 28, disease: 'FSME', location: 'Chemnitz', date: '2025-09-17', status: 'Aktiv' },
       { id: 29, disease: 'Hantavirus', location: 'Kiel', date: '2025-09-16', status: 'Geheilt' },
       { id: 30, disease: 'Q-Fieber', location: 'Aachen', date: '2025-09-15', status: 'Unter Beobachtung' },
       { id: 31, disease: 'Brucellose', location: 'Krefeld', date: '2025-09-14', status: 'Aktiv' },
       { id: 32, disease: 'Diphtherie', location: 'Halle', date: '2025-09-13', status: 'Behandelt' },
       { id: 33, disease: 'Polio', location: 'Magdeburg', date: '2025-09-12', status: 'Aktiv' },
       { id: 34, disease: 'Hepatitis C', location: 'Freiburg', date: '2025-09-11', status: 'Geheilt' },
       { id: 35, disease: 'Hepatitis E', location: 'Lübeck', date: '2025-09-10', status: 'Unter Beobachtung' },
       { id: 36, disease: 'Rotavirus', location: 'Erfurt', date: '2025-09-09', status: 'Aktiv' },
       { id: 37, disease: 'Adenovirus', location: 'Oberhausen', date: '2025-09-08', status: 'Behandelt' },
       { id: 38, disease: 'RSV', location: 'Rostock', date: '2025-09-07', status: 'Aktiv' },
       { id: 39, disease: 'Ringelröteln', location: 'Kassel', date: '2025-09-06', status: 'Geheilt' },
       { id: 40, disease: 'Pfeiffersches Drüsenfieber', location: 'Mainz', date: '2025-09-05', status: 'Unter Beobachtung' },
       { id: 41, disease: 'Krätze', location: 'Hamm', date: '2025-09-04', status: 'Aktiv' },
       { id: 42, disease: 'Tuberkulose', location: 'Saarbrücken', date: '2025-09-03', status: 'Behandelt' },
       { id: 43, disease: 'Campylobacter', location: 'Hagen', date: '2025-09-02', status: 'Aktiv' },
       { id: 44, disease: 'Yersiniose', location: 'Mülheim', date: '2025-09-01', status: 'Geheilt' },
       { id: 45, disease: 'Shigellose', location: 'Oldenburg', date: '2025-08-31', status: 'Unter Beobachtung' },
       { id: 46, disease: 'Giardiasis', location: 'Leverkusen', date: '2025-08-30', status: 'Aktiv' },
       { id: 47, disease: 'Cryptosporidiose', location: 'Osnabrück', date: '2025-08-29', status: 'Behandelt' },
       { id: 48, disease: 'Toxoplasmose', location: 'Solingen', date: '2025-08-28', status: 'Aktiv' },
       { id: 49, disease: 'Trichinellose', location: 'Ludwigshafen', date: '2025-08-27', status: 'Geheilt' },
       { id: 50, disease: 'Echinokokkose', location: 'Heidelberg', date: '2025-08-26', status: 'Unter Beobachtung' }
     ];

  constructor(private diseaseReportService: DiseaseReportService) {}

  ngOnInit(): void {
      // Original API call (commented out)
    /* this.diseaseReportService.getReports().subscribe((data: DiseaseReport[]) => {
      this.dataSource.data = data;
      this.dataSource.paginator = this.paginator;
      this.dataSource.sort = this.sort;
    }); */

// Use static data instead of API call
    this.dataSource.data = this.staticData;
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;

  }

  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.dataSource.filter = filterValue.trim().toLowerCase();

    if (this.dataSource.paginator) {
      this.dataSource.paginator.firstPage();
    }
  }
}