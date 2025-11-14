(function() {
    const days = document.querySelector(".days"),
    currentDate = document.querySelector(".current-date"),
    prevNextIcon = document.querySelectorAll(".icons span");

    let date = new Date(),
    currYear = date.getFullYear(),
    currMonth = date.getMonth();

    const months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Décembre"];

    function changeMonth(newMonth) {
        if(newMonth < 0 || newMonth > 11) {
            date = new Date(currYear, newMonth, new Date().getDate());
            currYear = date.getFullYear();
            currMonth = date.getMonth();
        } else date = new Date();
        renderCalendar();
    }

    const renderCalendar = () => {
        let firstDayOfMonth = new Date(currYear, currMonth, 0).getDay(),
        lastDateOfMonth = new Date(currYear, currMonth + 1, 0).getDate(),
        lastDayOfMonth = new Date(currYear, currMonth, lastDateOfMonth).getDay(),
        lastDateOfLastMonth = new Date(currYear, currMonth, 0).getDate();
        days.innerHTML = "";
        let weekCounter = 0;

        let ul = document.createElement("ul");
        for (let i = firstDayOfMonth; i > 0; --i) {
            let li = document.createElement("li");
            li.classList.add("inactive");
            li.innerText = lastDateOfLastMonth - i + 1;
            li.addEventListener("click", () => {
                changeMonth(--currMonth);
            });

            ul.append(li);
            ++weekCounter;
            if (weekCounter === 7) {
                days.append(ul);
                ul = document.createElement("ul");
                weekCounter = 0;
            }
        }

        for (let i = 1; i <= lastDateOfMonth; ++i) {
            let li = document.createElement("li");
            li.innerText = i;
            if(i === date.getDate() && currMonth === new Date().getMonth() && currYear === new Date().getFullYear()) {
                li.classList.add("active");
                li.classList.add("current");
            }
            li.addEventListener("click", () => {
                li.classList.add("active");
                let currentActive = document.querySelectorAll(".active");
                currentActive.forEach((activeEle) => {
                    if(activeEle !== li) activeEle.classList.remove("active");
                });
            });

            ul.append(li);
            ++weekCounter;
            if (weekCounter === 7) {
                days.append(ul);
                ul = document.createElement("ul");
                weekCounter = 0;
            }
        }

        for (let i = lastDayOfMonth; i < 7; ++i) {
            let li = document.createElement("li");
            li.classList.add("inactive");
            li.innerText = i - lastDayOfMonth + 1;
            li.addEventListener("click", () => {
                changeMonth(++currMonth);
            });

            ul.append(li);
            ++weekCounter;
            if (weekCounter === 7) {
                days.append(ul);
                ul = document.createElement("ul");
                weekCounter = 0;
            }
        }

        if (weekCounter > 0) {
            for (let i = 0; i<7-weekCounter; ++i) {
                ul.append(document.createElement("li"));
            }
            days.append(ul);
        }
        currentDate.innerText = `${months[currMonth]} ${currYear}`;
    }

    renderCalendar();

    prevNextIcon.forEach(icon => {
        icon.addEventListener("click", () => {
            currMonth = (icon.id === "prev" ? (currMonth-1) : (currMonth+1));
            changeMonth(currMonth);
        });
    });
})();