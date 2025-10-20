package com.example.personservice;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/persons")
@CrossOrigin
public class PersonController {

    private final PersonService personService;

    public PersonController(PersonService service) {
        this.personService = service;
    }

    @GetMapping
    public List<Person> getAll() {
        return personService.getAll();
    }

    @PostMapping
    public Person add(@RequestBody Person person) {
        return personService.add(person);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        personService.delete(id);
    }
}