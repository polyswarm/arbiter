package main

import (
	"encoding/csv"
	"fmt"
	"os"
)

type CsvLine struct {
	Column1  string
	Column2  string
	Column3  string
	Column4  string
	Column5  string
	Column6  string
	Column7  string
	Column8  string
	Column9  string
	Column10 string
	Column11 string
	Column12 string
	Column13 string
	Column14 string
	Column15 string
	Column16 string
	Column17 string
	Column18 string
	Column19 string
	Column20 string
	Column21 string
	Column22 string
	Column23 string
	Column24 string
	Column25 string
	Column26 string
	Column27 string
	Column28 string
	Column29 string
	Column30 string
	Column31 string
	Column32 string
}

func main() {

	filename := "tmp/sample2.csv"

	// Open CSV file
	f, err := os.Open(filename)
	if err != nil {
		panic(err)
	}
	defer f.Close()

	// Read File into a Variable
	lines, err := csv.NewReader(f).ReadAll()
	if err != nil {
		panic(err)
	}

	// Loop through lines & turn into object
	for _, line := range lines {
		data := CsvLine{
			Column1:  line[0],
			Column2:  line[1],
			Column3:  line[2],
			Column4:  line[3],
			Column5:  line[4],
			Column6:  line[5],
			Column7:  line[6],
			Column8:  line[7],
			Column9:  line[8],
			Column10: line[9],
			Column11: line[10],
			Column12: line[11],
			Column13: line[12],
			Column14: line[13],
			Column15: line[14],
			Column16: line[15],
			Column17: line[16],
			Column18: line[17],
			Column19: line[18],
			Column20: line[19],
			Column21: line[20],
			Column22: line[21],
			Column23: line[22],
			Column24: line[23],
			Column25: line[24],
			Column26: line[25],
			Column27: line[26],
			Column28: line[27],
			Column29: line[28],
			Column30: line[29],
			Column31: line[30],
			Column32: line[31],
		}

		//  fmt.Println(data.Column1 + " " + data.Column9 + " " + data.Column10 + " " + data.Column11 + " " + data.Column12 + " " + data.Column13 + " " + data.Column14 + " " + data.Column15 + " " + data.Column16 + " " + data.Column17 + " " + data.Column18 + " " + data.Column19)

		if data.Column9 == "0" {
			fmt.Println(data.Column1, data.Column9, " is Malicious")
		} else if data.Column9 == "1" {
			fmt.Println(data.Column1, data.Column9, " is Benign")
		} else {
			fmt.Println(data.Column1, data.Column9, " is unknown")
		}

	}
}
