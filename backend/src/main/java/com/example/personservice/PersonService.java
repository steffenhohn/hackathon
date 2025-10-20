package com.example.personservice;

import org.springframework.stereotype.Service;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class PersonService {
    private final Map<Long, Person> persons = new HashMap<>();
    private final AtomicLong idCounter = new AtomicLong();

    public List<Person> getAll() {
        return new ArrayList<>(persons.values());
    }

    public Person add(Person person) {
        long id = idCounter.incrementAndGet();
        person.setId(id);
        persons.put(id, person);
        return person;
    }

    public boolean delete(Long id) {
        return persons.remove(id) != null;
    }
}