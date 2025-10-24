import { Component, OnInit } from '@angular/core';
import { ChartConfiguration } from 'chart.js';
import { Person } from '../../models/person.model';
import { PersonService } from '../../services/person.service';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html'
})

export class DashboardComponent implements OnInit {
  persons: Person[] = [];
  filtered: Person[] = [];
  ageRange = { min: 0, max: 100 };

  public pieChartData = {
    labels: [],
    datasets: [
      {
        data: [],
        backgroundColor: [],
      }
    ]
  };
  public pieChartOptions: ChartConfiguration<'pie'>['options'] = {
    responsive: true
  };
  public pieChartType: 'pie' = 'pie';

  constructor(private personService: PersonService) {}

  ngOnInit() {
    this.personService.getAll().subscribe(data => {
      this.persons = data;
      //this.pieChartData = [1, 2, 3];
      this.updateChart();
      //this.filtered = this.persons.filter(p => p.age >= this.ageRange.min && p.age <= this.ageRange.max);
    });
  }

  updateChart(): void {
    const buckets = [0, 0, 0]; // 0-10, 11-60, 61-110

    for (const p of this.persons) {
      if (p.age <= 10) {
        buckets[0]++;
      } else if (p.age <= 60) {
        buckets[1]++;
      } else {
        buckets[2]++;
      }
    }

    this.pieChartData = {
        labels: ['0-10', '11-60', '61-110'],
        datasets: [
          {
            data: buckets,
            backgroundColor: ['#007bff', '#28a745', '#dc3545'],
          }
        ]
      };
  }
}