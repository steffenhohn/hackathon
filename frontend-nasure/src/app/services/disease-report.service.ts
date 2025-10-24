import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { DiseaseReport } from '../models/disease-report.model';

@Injectable({
  providedIn: 'root'
})
export class DiseaseReportService {
  private apiUrl = 'https://api.example.com/disease-reports';

  constructor(private http: HttpClient) {}

  getReports(): Observable<DiseaseReport[]> {
    return this.http.get<DiseaseReport[]>(this.apiUrl);
  }
}