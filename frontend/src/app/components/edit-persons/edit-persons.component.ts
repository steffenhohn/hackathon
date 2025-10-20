import { Component, OnInit } from '@angular/core';
import { Person } from '../../models/person.model';
import { PersonService } from '../../services/person.service';

@Component({
  selector: 'app-edit-persons',
  templateUrl: './edit-persons.component.html'
})

export class EditPersonsComponent implements OnInit {
  persons: Person[] = [];
  newPerson: Person = { name: '', age: 0 };

  constructor(private personService: PersonService) {}

  ngOnInit() {
    this.load();
  }

  load() {
    this.personService.getAll().subscribe(p => this.persons = p);
  }

  add() {
    this.personService.add(this.newPerson).subscribe(() => this.load());
  }

  remove(id: number) {
    this.personService.delete(id).subscribe(() => this.load());
  }
}